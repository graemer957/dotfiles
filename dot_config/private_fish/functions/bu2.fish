function bu2
    rsync -avzh --delete Downloads trinity:MBH102258
    rsync -avzh --delete dev trinity:MBH102258
    rsync -avzh --delete rustlings trinity:MBH102258
end
