# Lock-File
Python module to manipulate and lock files while in use.

## Warning
At the moment a real blocking is only achieved on Windows, on the other platforms only a warning will be produced, so it will still be possible to manipulate the files from external programs.

## Documentation:
### LockFile(filename: str=None, mode: str=None, encoding: str=None) (class)
Class for opening files. If only the file name or mode is passed as an argument when creating the class, an exception will be generated. The arguments are the same as the **LockFile.Open** method.

### LockFile.Open(filename: str, mode: str, encoding: str=None) (method)
Opens the specified file. As argument this class accepts the following:

**filename:** A string with the name of the file to be manipulated.

**mode:** A string with the mode in which you want to manipulate the file. Valid modes are:
  * **w:** To open files in write mode. If the file exists it will be replaced by a new one that is completely empty.
  * **wb:** Same as **"w"** mode but in binary.
  * **r:** To open files in read mode. If the file does not exist an exception is thrown.
  * **rb:** Same as **"r"** mode but in binary.
  * **a:** To open files in write mode. Unlike the **"w"** mode when a file is opened in this mode the data contained in the file is kept and the cursor is positioned on the last character, and if the file does not exist an exception is thrown.
  * **ab:** Same as **"a"** mode but in binary.
  * **rw:** To open files in write and read mode. If the file does not exist it is created and if it does exist it is opened without altering its content, positioning the cursor at the beginning.
  * **rwb:** Same as **"rw"** mode but in binary.

**encoding:** This argument is only used on non-Windows operating systems. On Windows, UTF-8 is used by default or ISO-8859-1 if UTF-8 fails. If this argument is left **None**, UTF-8 will be used by default.

### LockFile.Write(data) (method)
This method is used to write data to the file, accepting byte literals and strings, depending on whether the file was opened in binary mode or not.

### LockFile.Read(n_chars: int=-1) (str or bytes) (method)
This method is to read the data or characters contained in the file, returning a byte or string literal depending on whether the file was opened in binary mode or not.

In Windows if the file was opened in non-binary read mode the data or characters read will be encoded in UTF-8 or ISO-8859-1 and in other systems such as Linux they will be encoded in the one chosen by the user.

Argument:

**n_chars:** An integer that can be positive or negative, which will determine the number of characters that will be read. When this argument is **-1** it returns all remaining characters. This argument when negative is used in the same way as this expression **"text[:-1]"**, so passing as argument **-5** will return all remaining characters but the last **4**.

### LockFile.Seek(offset: int, startpoint: str="current") (return int) (method)
This method is to position the file cursor where desired. Returns an integer with the new position.

Arguments:

**offset:** A positive or negative integer that will indicate how many characters the cursor should be moved.

**startpoint:** A string to determine where to start moving the cursor from, the keywords that can be used are the following:
  * **begin:** To start from the zero position or the beginning.
  * **current:** To start from the current cursor position.
  * **end:** To start from the end.

### LockFile.Seek2(pos: int) (return int) (method)
Unlike the **"Seek"** method, this method positions the cursor at the specified position and not in a scrolling manner. Returns an integer with the new position.

It works in the same way as the **"seek"** method of **"open"**, also this is equivalent to **LockFile.Seek(pos, "begin")**.

### LockFile.Close() (method)
Close the file.

### LockFile.GetFileSize() (return int) (method)
The current file size is obtained.

### LockFile.GetCursorPos() (return int) (method)
The current cursor position is obtained, it is equivalent to calling **LockFile.Seek(0, "current")**.

### LockFile.IsWriteable() (return bool) (method)
Returns True if the file is writable and False otherwise.

### LockFile.IsReadable() (return bool) (method)
Returns True if the file can be read and False if not.

### LockFile.IsBinary() (return bool) (method)
Returns True if the file is open in binary mode and False otherwise.

### Open(filename: str, mode: str, encoding: str=None) (return LockFile) (function)
This is the same as **LockFile("file", "mode", "encoding")** or **LockFile.Open("file", "mode", "encoding")**. See **LockFile.Open** for more about the arguments. Returns a **LockFile** object.

### MAXDATAPERITE (int) (variable)
This variable is used to determine the number of bytes to be read and/or written per iteration. The variable must always be a positive integer greater than zero and by default this variable has a value of 100000.