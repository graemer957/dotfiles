function rclone_data2_env
    set -x RCLONE_CRYPT_PASSWORD 'op://z6sddnfnoh7ur2his6xqtllhuy/vfueykvgqjghrfffttnyxv3id4/password'
    set -x RCLONE_CRYPT_PASSWORD2 "op://z6sddnfnoh7ur2his6xqtllhuy/vfueykvgqjghrfffttnyxv3id4/salt aka password2"

    op run -- rclone $argv
end
