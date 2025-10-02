tell application "Keynote"
    if (count of documents) is 0 then
        error "No open Keynote document"
    end if
    tell document 1
        set s to slide size
        set w to item 1 of s
        set h to item 2 of s
    end tell
end tell
return (w as string) & "|" & (h as string)
