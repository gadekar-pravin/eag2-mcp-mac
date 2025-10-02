on run argv
    set theID to item 1 of argv
    set theText to item 2 of argv
    tell application "Keynote"
        if (count of documents) is 0 then
            error "No open Keynote document"
        end if
        tell document 1
            tell slide 1
                set targetShape to (first shape whose id is theID)
                set object text of targetShape to theText
                try
                    tell object text of targetShape
                        set alignment to center
                    end tell
                end try
                try
                    set vertical alignment of targetShape to center
                end try
            end tell
        end tell
    end tell
    return (length of theText) as string
end run
