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


  val payload = TextIO.inputN (TextIO.stdIn, lengthInt)
  val () = TextIO.output (tmpFile, ("payload: " ^ payload ^ "\n"))
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
