function rclone_data1_env
    set -x RCLONE_CRYPT_PASSWORD 'op://jfabgjw6euv4xxc2e2oqqlbud4/247ru76s52vlusynqnmhaifomm/password'
    set -x RCLONE_CRYPT_PASSWORD2 "op://jfabgjw6euv4xxc2e2oqqlbud4/247ru76s52vlusynqnmhaifomm/salt aka password2"

    op run -- rclone $argv
end
