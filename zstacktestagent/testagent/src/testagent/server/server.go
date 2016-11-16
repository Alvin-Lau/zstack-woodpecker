package server

import (
	"net/http"
	"fmt"
	"testagent/utils"
	"time"
	"encoding/json"
	log "github.com/Sirupsen/logrus"
	"github.com/pkg/errors"
	"net/http/httputil"
	"bytes"
	"io/ioutil"
	"bufio"
)

type commandHandlerWrap struct {
	path string
	handler http.HandlerFunc
	async bool
}

type Options struct {
	Ip           string
	Port         uint
	ReadTimeout  uint
	WriteTimeout uint
	LogFile      string
	Type	     string
}


type CommandResponseHeader struct {
	Success bool `json:"success"`
	Error string `json:"error"`
}

type CommandContext struct {
	responseWriter http.ResponseWriter
	request *http.Request
}

func (ctx *CommandContext) GetCommand(cmd interface{}) {
	if err := utils.JsonDecodeHttpRequest(ctx.request, cmd); err != nil {
		panic(err)
	}
}

type CommandHandler func(ctx *CommandContext) interface{}

type HttpInterceptor func(http.HandlerFunc) http.HandlerFunc

var (
	commandHandlers map[string]*commandHandlerWrap = make(map[string]*commandHandlerWrap)
	commandOptions Options
)

const (
	CALLBACK_URL = "callbackurl"
	TASK_UUID = "taskuuid"
)

func SetOptions(o Options) {
	commandOptions = o
}

func RegisterSyncCommandHandler(path string, chandler CommandHandler)  {
	registerCommandHandler(path, chandler, false)
}

func RegisterAsyncCommandHandler(path string, chandler CommandHandler) {
	registerCommandHandler(path, chandler, true)
}

func registerCommandHandler(path string, chandler CommandHandler, async bool) {
	utils.Assert(path != "", "path cannot be nil")
	utils.Assert(chandler != nil, "chandler cannot be nil")

	if _, ok := commandHandlers[path]; ok {
		panic(fmt.Errorf("duplicate handler for the path[%v]", path))
	}

	w := &commandHandlerWrap{
		path: path,
		async: async,
	}

	syncReply := func(rsp interface{}, w http.ResponseWriter, req *http.Request) {
		var statusCode int
		var body string
		if b, err := json.Marshal(rsp); err == nil {
			statusCode = http.StatusOK
			body = string(b)
		} else {
			utils.LogError(err)
			statusCode = http.StatusInternalServerError
			body = err.Error()
		}

		log.Debugf("[RESPONSE] to %v, status code: %v, body: %v", req.URL, statusCode, body)
		w.WriteHeader(statusCode)
		utils.LogError(fmt.Fprint(w, body))
	}

	asyncReply := func(rsp interface{}, w http.ResponseWriter, req *http.Request) {
		callbackURL := req.Header.Get(CALLBACK_URL)
		taskUuid := req.Header.Get(TASK_UUID)
		err := utils.Retry(func() error {
			return utils.HttpPostForObject(callbackURL, map[string]string{
				TASK_UUID: taskUuid,
			}, rsp, nil)
		}, 60, 1); utils.LogError(err)
	}

	handler := func(w http.ResponseWriter, req *http.Request) {
		ctx := &CommandContext{
			responseWriter: w,
			request: req,
		}

		if !async {
			rsp := chandler(ctx)
			if rsp == nil {
				rsp = CommandResponseHeader{ Success: true }
			}
			syncReply(rsp, w, req)
		} else {
			// reply first, and the response body is ignored
			// this is an ack that we have received the request
			syncReply("", w, req)

			// do the real work and then send the response
			rsp := chandler(ctx)
			if rsp == nil {
				rsp = CommandResponseHeader{ Success: true }
			}

			asyncReply(rsp, w, req)
		}
	}

	w.handler = func(w http.ResponseWriter, req *http.Request) {
		defer func() {
			if err := recover(); err != nil {
				reply := CommandResponseHeader{
					Success: false,
					Error: fmt.Sprintf("%v", err),
				}

				if e, ok := err.(error); ok {
					log.Warnf("%+v\n", errors.Wrap(e, fmt.Sprintf("command[path:%s] failed", path)))
				} else {
					log.Warnf("%+v\n", errors.Wrap(errors.New(err.(string)), fmt.Sprintf("command[path:%s] failed", path)))
				}


				if !async {
					syncReply(reply, w, req)
				} else {
					asyncReply(reply, w, req)
				}
			}
		}()

		if reqDump, err := httputil.DumpRequest(req, true); err != nil {
			log.Warnf("unable to dump the http request[url:%v]", req.URL)
		} else {
			nreq, err := http.ReadRequest(bufio.NewReader(bytes.NewReader(reqDump))); utils.LogError(err)
			if nreq != nil {
				body, err := ioutil.ReadAll(nreq.Body); utils.LogError(err)
				defer nreq.Body.Close()
				log.WithFields(log.Fields{
					CALLBACK_URL: nreq.Header.Get(CALLBACK_URL),
					TASK_UUID: nreq.Header.Get(TASK_UUID),
					"Host": nreq.Header.Get("Host"),
				}).Debugf("[RECV] %v, body: %s", nreq.URL, string(body))
			}
		}

		handler(w, req)
	}

	log.Debugf("a command path[%s] is registered", path)
	commandHandlers[path] = w
}



func Start()  {
	startServer()
}

type dispatcher func(w http.ResponseWriter, req *http.Request)

func (d dispatcher) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	d(w, req)
}

func dispatch(w http.ResponseWriter, req *http.Request) {
	path := req.URL.Path
	wrap, ok := commandHandlers[path]
	if !ok {
		log.Warnf("no plugin registered the path[%s], drop it", path)
		w.WriteHeader(http.StatusNotFound)
		utils.LogError(fmt.Fprintf(w, "no plugin registered the path[%s]", path))
		return
	}

	if !wrap.async {
		wrap.handler(w, req)
		return
	}

	callbackURL := req.Header.Get(CALLBACK_URL)
	if callbackURL == "" {
		err := fmt.Sprintf("no field '%s' found in the HTTP header but the plugin registers the path[%s]" +
				" as an async command", CALLBACK_URL, path)
		log.Warn(err)
		w.WriteHeader(http.StatusBadRequest)
		utils.LogError(fmt.Fprint(w, err))
		return
	}

	taskUuid := req.Header.Get(TASK_UUID)
	if taskUuid == "" {
		err := fmt.Sprintf("no field '%s' found in the HTTP header but the plugin registers the path[%s]" +
				" as an async command", TASK_UUID, path)
		log.Warn(err)
		w.WriteHeader(http.StatusBadRequest)
		utils.LogError(fmt.Fprint(w, err))
		return
	}

	// for async command, reply first and then handle
	w.WriteHeader(http.StatusOK)
	utils.LogError(fmt.Fprint(w, ""))
	wrap.handler(w, req)
}

func startServer() {
	server := &http.Server{
		Addr: fmt.Sprintf("%v:%v", commandOptions.Ip, commandOptions.Port),
		ReadTimeout: time.Duration(commandOptions.ReadTimeout) * time.Second,
		WriteTimeout: time.Duration(commandOptions.WriteTimeout) * time.Second,
		Handler: dispatcher(dispatch),
	}

	log.Debugln("everything looks good, the agent starts ...")
	server.ListenAndServe()
}
