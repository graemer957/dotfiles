function rclone_data2_serve -d "Serve data2: via `rclone`"
    rclone_data2_env serve nfs data2: --addr 0.0.0.0:9572 --vfs-cache-mode=full -v
end
