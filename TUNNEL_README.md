# SSH Tunnel Installation Script

A robust script for installing and configuring persistent SSH tunnels on remote Ubuntu/Debian servers using SSH key-based authentication.

## Features

- ✅ SSH key-based authentication (secure)
- ✅ Automatic installation of `autossh` on remote servers
- ✅ Persistent tunnels using systemd services
- ✅ Support for both local and remote port forwarding
- ✅ Batch installation from configuration file
- ✅ Automatic reconnection on connection drops
- ✅ Comprehensive error handling and logging

## Prerequisites

1. **SSH Key**: You need an SSH private key to connect to remote servers
   ```bash
   # Generate one if needed
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
   ```

2. **SSH Key on Remote Servers**: Copy your public key to remote servers
   ```bash
   ssh-copy-id user@remote-server
   ```

3. **Remote Server Requirements**:
   - Ubuntu/Debian-based system
   - SSH access with sudo privileges
   - Network connectivity

## Quick Start

### 1. Install autossh on a single server

```bash
./install_ssh_tunnel.sh -s 192.168.1.100 -u admin
```

### 2. Create a local persistent tunnel

Forward local port 8080 to remote server's port 80:

```bash
./install_ssh_tunnel.sh -s 192.168.1.100 -u admin -l 8080 -r 80 -p
```

Now you can access the remote web server at `http://localhost:8080`

### 3. Create a remote tunnel

Expose your local service (port 3000) on remote server's port 8000:

```bash
./install_ssh_tunnel.sh -s 192.168.1.100 -u admin -l 3000 -r 8000 -m remote -p
```

### 4. Batch installation

Edit `tunnel_config.txt` with your servers and run:

```bash
./install_ssh_tunnel.sh -c tunnel_config.txt
```

## Usage

```
./install_ssh_tunnel.sh [OPTIONS]

Options:
    -h, --help              Show help message
    -s, --server HOST       Remote server hostname or IP
    -u, --user USER         SSH user (default: root)
    -k, --key PATH          Path to SSH private key (default: ~/.ssh/id_rsa)
    -c, --config FILE       Use configuration file for batch installation

    Tunnel Configuration:
    -l, --local-port PORT   Local port to forward
    -r, --remote-port PORT  Remote port to forward to
    -t, --target HOST       Target host (default: localhost)
    -m, --mode MODE         Tunnel mode: 'local' or 'remote' (default: local)
    -p, --persistent        Create persistent tunnel using systemd
```

## Tunnel Types

### Local Tunnel (`-m local`)
Forward a local port to a remote port. Use this to access remote services locally.

**Example**: Access remote MySQL database locally
```bash
./install_ssh_tunnel.sh -s db.example.com -u admin -l 3306 -r 3306 -p
# Connect to MySQL: mysql -h 127.0.0.1 -P 3306
```

### Remote Tunnel (`-m remote`)
Forward a remote port to a local port. Use this to expose local services to the remote server.

**Example**: Expose local development server to remote
```bash
./install_ssh_tunnel.sh -s staging.example.com -u admin -l 3000 -r 8000 -m remote -p
# Your local:3000 is now accessible on staging.example.com:8000
```

## Configuration File Format

Create a `tunnel_config.txt` file with the following format:

```csv
server_host,ssh_user,local_port,remote_host,remote_port,tunnel_type,persistent
192.168.1.100,admin,8080,localhost,80,local,yes
192.168.1.101,root,3306,localhost,3306,local,yes
192.168.1.102,deploy,3000,localhost,8000,remote,yes
```

Fields:
- `server_host`: Remote server IP or hostname
- `ssh_user`: SSH username
- `local_port`: Local port number
- `remote_host`: Target host (usually 'localhost')
- `remote_port`: Remote/target port number
- `tunnel_type`: 'local' or 'remote'
- `persistent`: 'yes' for systemd service, 'no' for manual

## Managing Tunnels

### Check tunnel status

```bash
ssh user@remote-server "sudo systemctl status ssh-tunnel-8080"
```

### Stop a tunnel

```bash
ssh user@remote-server "sudo systemctl stop ssh-tunnel-8080"
```

### Start a tunnel

```bash
ssh user@remote-server "sudo systemctl start ssh-tunnel-8080"
```

### Restart a tunnel

```bash
ssh user@remote-server "sudo systemctl restart ssh-tunnel-8080"
```

### View tunnel logs

```bash
ssh user@remote-server "sudo journalctl -u ssh-tunnel-8080 -f"
```

### List all tunnel services

```bash
ssh user@remote-server "sudo systemctl list-units 'ssh-tunnel-*'"
```

### Remove a tunnel

```bash
ssh user@remote-server "sudo systemctl stop ssh-tunnel-8080 && sudo systemctl disable ssh-tunnel-8080 && sudo rm /etc/systemd/system/ssh-tunnel-8080.service && sudo systemctl daemon-reload"
```

## Environment Variables

- `SSH_KEY`: Path to SSH private key (default: `~/.ssh/id_rsa`)
- `SSH_USER`: Default SSH user (default: `root`)

Example:
```bash
export SSH_KEY=~/.ssh/my_key
export SSH_USER=admin
./install_ssh_tunnel.sh -s 192.168.1.100 -l 8080 -r 80 -p
```

## Common Use Cases

### 1. Access remote database locally

```bash
# PostgreSQL
./install_ssh_tunnel.sh -s db-server -u postgres -l 5432 -r 5432 -p

# MySQL
./install_ssh_tunnel.sh -s db-server -u mysql -l 3306 -r 3306 -p

# MongoDB
./install_ssh_tunnel.sh -s db-server -u mongo -l 27017 -r 27017 -p
```

### 2. Access remote web application

```bash
./install_ssh_tunnel.sh -s app-server -u admin -l 8080 -r 80 -p
# Visit http://localhost:8080
```

### 3. Expose local service to remote server

```bash
./install_ssh_tunnel.sh -s remote-server -u admin -l 3000 -r 8000 -m remote -p
```

### 4. SSH jump host / bastion

```bash
./install_ssh_tunnel.sh -s bastion -u admin -l 2222 -t internal-server -r 22 -p
# SSH to internal server: ssh -p 2222 user@localhost
```

## Troubleshooting

### Connection issues

1. Verify SSH key permissions:
   ```bash
   chmod 600 ~/.ssh/id_rsa
   ```

2. Test SSH connection manually:
   ```bash
   ssh -i ~/.ssh/id_rsa user@remote-server
   ```

3. Check if port is already in use:
   ```bash
   sudo lsof -i :8080
   ```

### Tunnel not working

1. Check service status:
   ```bash
   ssh user@remote-server "sudo systemctl status ssh-tunnel-8080"
   ```

2. View logs:
   ```bash
   ssh user@remote-server "sudo journalctl -u ssh-tunnel-8080 -n 50"
   ```

3. Test autossh manually:
   ```bash
   ssh user@remote-server "autossh -M 0 -N -L 8080:localhost:80 -o ServerAliveInterval=30 target-server"
   ```

### Port already in use

```bash
# Find process using the port
sudo lsof -i :8080
# Kill the process
sudo kill -9 <PID>
```

## Security Considerations

1. **Use SSH keys**: Never use password authentication for automated tunnels
2. **Restrict SSH access**: Configure `~/.ssh/authorized_keys` with command restrictions if needed
3. **Firewall rules**: Only expose necessary ports
4. **Monitor tunnels**: Regularly check tunnel logs for suspicious activity
5. **Use strong keys**: Generate RSA keys with at least 2048 bits (4096 recommended)

## Advanced Configuration

### Custom autossh options

Edit the systemd service file on the remote server:

```bash
sudo nano /etc/systemd/system/ssh-tunnel-8080.service
```

Add custom SSH options to `ExecStart`:
```ini
ExecStart=/usr/bin/autossh -M 0 -N -L 8080:localhost:80 \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -o StrictHostKeyChecking=no \
    -o ExitOnForwardFailure=yes \
    -o Compression=yes \
    -o TCPKeepAlive=yes \
    target-server
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ssh-tunnel-8080
```

## License

MIT License - Feel free to use and modify as needed.
