on run argv
    set xVal to (item 1 of argv) as integer
    set yVal to (item 2 of argv) as integer
    set wVal to (item 3 of argv) as integer
    set hVal to (item 4 of argv) as integer

    tell application "Keynote"
        if (count of documents) is 0 then error "No open Keynote document"
        tell document 1
            tell slide 1
                -- Create first, then set properties (avoids fragile "with properties {...}" record)
                set newShape to make new shape
                set position of newShape to {xVal, yVal}
                set width of newShape to wVal
                set height of newShape to hVal
                try
                    set shape type of newShape to rectangle
                end try
                set theID to id of newShape
            end tell
        end tell
    end tell

    return theID as string
end run
