1) Check [this](https://support.checkpoint.com/results/sk/sk119772) page and search for the required tools and libraries for your Linux distribution.

2) Inside repository home folder, give permissions to `cshell_install.sh` file
```
sudo chmod +x cshell_install.sh
```

3) Close all your opened browsers (if any) and run the following script to start installation process
```
sudo sh cshell_install.sh
```

:warning: **Warning**: before you proceed, make sure your Linux OS uses `systemd` as a service manager

3) Copy `checkpoint.service` file from `src` folder to `~/.config/systemd/user`

```
cp src/checkpoint.service ~/.config/systemd/user
```

and create a `systemd` service
```
systemctl --user enable checkpoint.service
```

to check service status run
```
systemctl --user status checkpoint.service
```

4) Create a file called **.snxrc** in your user home folder and paste the following content, replacing "user@ua.pt" by your UA email
```
server go.ua.pt
username user@ua.pt
reauth yes
```

5) You are now ready to rock!

connect
```
snx
```

disconnect
```
snx -d
```
