tell application "Keynote"
    if (count of documents) is 0 then error "No open Keynote document"
    set docRef to document 1
    set w to missing value
    set h to missing value
    repeat with attempt from 1 to 5
        try
            tell docRef
                set w to width
                set h to height
            end tell
            exit repeat
        on error errMsg number errNum
            if attempt is 5 then error errMsg number errNum
            delay 0.2
        end try
    end repeat
end tell
return (w as string) & "|" & (h as string)
