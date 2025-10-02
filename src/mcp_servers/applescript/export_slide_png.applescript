on run argv
    set outPath to item 1 of argv
    tell application "Keynote"
        if (count of documents) is 0 then
            error "No open Keynote document"
        end if
        tell document 1
            set t to POSIX file outPath
            export it to t as PNG with properties {slides:{1}, resolution:144}
        end tell
    end tell
    return outPath
end run
