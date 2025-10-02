on ensure_new_document(themeName)
    tell application "Keynote"
        try
            return make new document with properties {document theme:theme themeName}
        on error
            return make new document with properties {document theme:theme "White"}
        end try
    end tell
end ensure_new_document

on run argv
    set themeName to item 1 of argv
    set docMode to item 2 of argv
    tell application "Keynote"
        activate
        set frontmost to true
        if docMode is "always_new" then
            set docRef to my ensure_new_document(themeName)
        else
            if (count of documents) is 0 then
                set docRef to my ensure_new_document(themeName)
            else
                set docRef to document 1
            end if
        end if
        tell docRef
            set currentSlide to slide 1
            set s to slide size
            set w to item 1 of s
            set h to item 2 of s
        end tell
    end tell
    return (w as string) & "|" & (h as string)
end run
