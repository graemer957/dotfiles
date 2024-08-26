function rclone_data2_mount -d "Mount data2: from `rclone serve`"
    mount -oport=9572,mountport=9572 localhost: ~/data2
end
