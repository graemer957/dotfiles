function rclone_data2_mount_l -d "Mount data2: from r2"
    rclone_data2_env mount data2: /mnt/data2 -v
end
