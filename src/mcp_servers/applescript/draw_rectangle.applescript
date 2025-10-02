on run argv
    set xVal to (item 1 of argv) as integer
    set yVal to (item 2 of argv) as integer
    set wVal to (item 3 of argv) as integer
    set hVal to (item 4 of argv) as integer
    tell application "Keynote"
        if (count of documents) is 0 then
            error "No open Keynote document"
        end if
        tell document 1
            tell slide 1
                set newShape to make new shape with properties {shape type:rectangle, position:{xVal, yVal}, width:wVal, height:hVal}
                set theID to id of newShape
            end tell
        end tell
    end tell
    return theID as string
end run
