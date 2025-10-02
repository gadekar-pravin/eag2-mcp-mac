on run argv
    -- argv[1] = themeName (ignored), argv[2] = docMode ("reuse_or_create" | "always_new")
    set themeName to item 1 of argv
    set docMode to item 2 of argv

    tell application "Keynote"
        activate

        -- Create or reuse a document using only stable verbs
        if docMode is "always_new" then
            set docRef to make new document
        else
            if (count of documents) is 0 then
                set docRef to make new document
            else
                set docRef to document 1
            end if
        end if

        -- Ensure there's at least one slide (paranoia)
        if (count of slides of docRef) is 0 then
            tell docRef to make new slide at end
        end if

        -- Robustly retrieve dimensions via document properties
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
end run
