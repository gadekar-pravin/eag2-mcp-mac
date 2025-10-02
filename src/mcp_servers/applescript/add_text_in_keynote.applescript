on run argv
    set theIndex to item 1 of argv as integer
    set theText to item 2 of argv
    tell application "Keynote"
        if (count of documents) is 0 then
            error "No open Keynote document"
        end if
        tell document 1
            tell slide 1
                set targetShape to shape theIndex
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