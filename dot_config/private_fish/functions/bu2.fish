function bu2
    rsync -avzh --delete Code switch:MBH102258
    rsync -avzh --delete Downloads switch:MBH102258
    rsync -avzh --delete dev switch:MBH102258
    rsync -avzh --delete rustlings switch:MBH102258
end
