function rclone_data1_serve -d "Serve data1: via `rclone`"
    rclone_data1_env serve nfs data1: --addr 0.0.0.0:9571 --vfs-cache-mode=full -v
end
