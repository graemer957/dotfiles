function rclone_data1_mount -d "Mount data1: from `rclone serve`"
    mount -oport=9571,mountport=9571 localhost: ~/data1
end
