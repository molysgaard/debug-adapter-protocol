structure Handlers : HANDLERS = struct
    val handleCancel : CancelRequest.t -> CancelResponse.t
    val handleRunInTerminal : RunInTerminalRequest.t -> RunInTerminalResponse.t
    val handleInitialize : InitializeRequest.t -> InitializeResponse.t
    val handleConfigurationDone : ConfigurationDoneRequest.t -> ConfigurationDoneResponse.t
    val handleLaunch : LaunchRequest.t -> LaunchResponse.t
    val handleAttach : AttachRequest.t -> AttachResponse.t
    val handleRestart : RestartRequest.t -> RestartResponse.t
    val handleDisconnect : DisconnectRequest.t -> DisconnectResponse.t
    val handleTerminate : TerminateRequest.t -> TerminateResponse.t
    val handleBreakpointLocations : BreakpointLocationsRequest.t -> BreakpointLocationsResponse.t
    val handleSetBreakpoints : SetBreakpointsRequest.t -> SetBreakpointsResponse.t
    val handleSetFunctionBreakpoints : SetFunctionBreakpointsRequest.t -> SetFunctionBreakpointsResponse.t
    val handleSetExceptionBreakpoints : SetExceptionBreakpointsRequest.t -> SetExceptionBreakpointsResponse.t
    val handleDataBreakpointInfo : DataBreakpointInfoRequest.t -> DataBreakpointInfoResponse.t
    val handleSetDataBreakpoints : SetDataBreakpointsRequest.t -> SetDataBreakpointsResponse.t
    val handleSetInstructionBreakpoints : SetInstructionBreakpointsRequest.t -> SetInstructionBreakpointsResponse.t
    val handleContinue : ContinueRequest.t -> ContinueResponse.t
    val handleNext : NextRequest.t -> NextResponse.t
    val handleStepIn : StepInRequest.t -> StepInResponse.t
    val handleStepOut : StepOutRequest.t -> StepOutResponse.t
    val handleStepBack : StepBackRequest.t -> StepBackResponse.t
    val handleReverseContinue : ReverseContinueRequest.t -> ReverseContinueResponse.t
    val handleRestartFrame : RestartFrameRequest.t -> RestartFrameResponse.t
    val handleGoto : GotoRequest.t -> GotoResponse.t
    val handlePause : PauseRequest.t -> PauseResponse.t
    val handleStackTrace : StackTraceRequest.t -> StackTraceResponse.t
    val handleScopes : ScopesRequest.t -> ScopesResponse.t
    val handleVariables : VariablesRequest.t -> VariablesResponse.t
    val handleSetVariable : SetVariableRequest.t -> SetVariableResponse.t
    val handleSource : SourceRequest.t -> SourceResponse.t
    val handleThreads : ThreadsRequest.t -> ThreadsResponse.t
    val handleTerminateThreads : TerminateThreadsRequest.t -> TerminateThreadsResponse.t
    val handleModules : ModulesRequest.t -> ModulesResponse.t
    val handleLoadedSources : LoadedSourcesRequest.t -> LoadedSourcesResponse.t
    val handleEvaluate : EvaluateRequest.t -> EvaluateResponse.t
    val handleSetExpression : SetExpressionRequest.t -> SetExpressionResponse.t
    val handleStepInTargets : StepInTargetsRequest.t -> StepInTargetsResponse.t
    val handleGotoTargets : GotoTargetsRequest.t -> GotoTargetsResponse.t
    val handleCompletions : CompletionsRequest.t -> CompletionsResponse.t
    val handleExceptionInfo : ExceptionInfoRequest.t -> ExceptionInfoResponse.t
    val handleReadMemory : ReadMemoryRequest.t -> ReadMemoryResponse.t
    val handleDisassemble : DisassembleRequest.t -> DisassembleResponse.t
end

struct DAP = DebugAdapterProtocol(structure Handlers = Handlers)

fun parseMessage tmpFile () = let
  val contentLength = valOf (TextIO.inputLine TextIO.stdIn)
  val () = TextIO.output (tmpFile, ("inputLine: " ^ contentLength ^ "\n"))
  val () = TextIO.flushOut tmpFile

  val field = "Content-Length: "
  val isCorrectField = (String.substring (contentLength, 0, String.size field) = field)
  val () = TextIO.output (tmpFile, ("isCorrectField: " ^ (Bool.toString isCorrectField) ^ " " ^ (Int.toString (String.size field)) ^ " " ^ (Int.toString (String.size contentLength)) ^ "\n"))
  val () = TextIO.flushOut tmpFile

  val () = TextIO.output (tmpFile, ("nowstring: " ^ contentLength ^ "\n"))
  val () = TextIO.flushOut tmpFile
  val lengthStrInt = String.substring (contentLength, String.size field,
  (String.size contentLength) - (String.size field + 2))
  val () = TextIO.output (tmpFile, ("lengthStrInt: " ^ lengthStrInt ^ "\n"))
  val () = TextIO.flushOut tmpFile
  val lengthInt = valOf (Int.fromString lengthStrInt)
  val () = TextIO.output (tmpFile, ("lengthInt: " ^ (Int.toString lengthInt) ^ "\n"))
  val () = TextIO.flushOut tmpFile

  val empty = valOf (TextIO.inputLine TextIO.stdIn)
  val isEmpty = (empty = "\r\n")
  val () = TextIO.output (tmpFile, ("isEmpty: " ^ (Bool.toString isEmpty) ^ "\n"))
  val () = TextIO.flushOut tmpFile


  val payloadString = TextIO.inputN (TextIO.stdIn, lengthInt)
  val payloadJson = (JSONParser.parse (TextIO.openString payloadString))
  val () = TextIO.output (tmpFile, ("payloadJson: "))
  val () = JSONPrinter.print (tmpFile, payloadJson)
  val () = TextIO.flushOut tmpFile

  val responseJson = DAP.handleRequest payloadJson
  val () = TextIO.output (tmpFile, ("responseJson: "))
  val () = JSONPrinter.print (tmpFile, responseJson)
  val () = TextIO.flushOut tmpFile

  val eof = TextIO.endOfStream TextIO.stdIn
in
  not eof
end

fun printAndLogLines tmpFile () =
  let
    val message = TextIO.input TextIO.stdIn
    val () = TextIO.output (tmpFile, message)
    (* val () = TextIO.print message; *)
    val eof = TextIO.endOfStream TextIO.stdIn
  in
    not eof
  end

fun loop action = let
  val continue = action ()
in
  case continue of
       true => loop action
     | false => ()
end

val tmpFile = TextIO.openOut "/tmp/smlLog.txt"
val () = loop (parseMessage tmpFile)
val () = TextIO.closeOut tmpFile
