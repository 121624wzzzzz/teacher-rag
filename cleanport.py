import os
import sys
import signal
import subprocess
import time

def find_process_by_port(port):
    """尝试查找占用指定端口的进程"""
    pid = None
    
    # 尝试使用不同的系统命令
    commands = [
        f"netstat -tlnp 2>/dev/null | grep ':{port}'",
        f"ss -tlnp 2>/dev/null | grep ':{port}'",
        f"ps aux | grep 'uvicorn' | grep -v grep"
    ]
    
    for cmd in commands:
        try:
            output = subprocess.check_output(cmd, shell=True).decode('utf-8')
            print(f"Command output: {output}")
            
            if output:
                # 从netstat或ss输出中提取PID
                if 'netstat' in cmd or 'ss' in cmd:
                    for line in output.splitlines():
                        if f":{port}" in line:
                            # 尝试提取PID
                            parts = line.split()
                            for part in parts:
                                if '/' in part:  # pid/program_name 格式
                                    try:
                                        pid = int(part.split('/')[0])
                                        return pid
                                    except:
                                        pass
                
                # 从ps输出中提取所有Python/uvicorn进程
                elif 'ps' in cmd:
                    for line in output.splitlines():
                        parts = line.split()
                        if len(parts) > 1:
                            try:
                                pid = int(parts[1])  # PID通常是第二列
                                return pid
                            except:
                                continue
        except Exception as e:
            print(f"Error running command {cmd}: {e}")
    
    return None

def kill_process(pid):
    """尝试杀死指定的进程"""
    if not pid:
        return False
    
    try:
        # 先尝试正常终止
        os.kill(pid, signal.SIGTERM)
        print(f"已发送SIGTERM到进程 {pid}")
        
        # 给进程一些时间正常退出
        time.sleep(2)
        
        # 检查进程是否仍在运行
        try:
            os.kill(pid, 0)  # 如果进程不存在，会抛出异常
            # 进程仍在运行，强制终止
            os.kill(pid, signal.SIGKILL)
            print(f"已发送SIGKILL到进程 {pid}")
        except OSError:
            # 进程已经终止
            pass
            
        return True
    except Exception as e:
        print(f"杀死进程时出错: {e}")
        return False

def is_port_free(port):
    """检查端口是否可用"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def main():
    port = 8003
    
    print(f"检查端口 {port}...")
    
    if is_port_free(port):
        print(f"端口 {port} 已可用，无需清理")
        return True
    
    print(f"端口 {port} 被占用，尝试清理...")
    
    # 查找并杀死占用端口的进程
    pid = find_process_by_port(port)
    
    if pid:
        print(f"找到占用端口 {port} 的进程: {pid}")
        if kill_process(pid):
            print(f"成功终止进程 {pid}")
            
            # 再次检查端口
            time.sleep(2)
            if is_port_free(port):
                print(f"端口 {port} 已释放")
                return True
            else:
                print(f"端口 {port} 仍被占用，可能有其他进程")
        else:
            print(f"无法终止进程 {pid}")
    else:
        print(f"未找到占用端口 {port} 的进程")
        
        # 尝试杀死所有uvicorn相关进程
        try:
            output = subprocess.check_output("ps aux | grep uvicorn | grep -v grep", shell=True).decode('utf-8')
            for line in output.splitlines():
                try:
                    pid = int(line.split()[1])
                    print(f"尝试终止uvicorn进程 {pid}")
                    kill_process(pid)
                except:
                    continue
                    
            # 再次检查端口
            time.sleep(2)
            if is_port_free(port):
                print(f"端口 {port} 已释放")
                return True
        except:
            pass
    
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)