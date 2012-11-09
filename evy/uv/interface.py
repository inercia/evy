#
# Evy - a concurrent networking library for Python
#
# Unless otherwise noted, the files in Evy are under the following MIT license:
#
# Copyright (c) 2012, Alvaro Saurin
# Copyright (c) 2008-2010, Eventlet Contributors (see AUTHORS)
# Copyright (c) 2007-2010, Linden Research, Inc.
# Copyright (c) 2005-2006, Bob Ippolito
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

from __future__ import absolute_import
import sys, os

__here__ = os.path.dirname(__file__)

LIBUV_DIR = os.path.join(__here__, '..', '..', 'libuv')
LIBUV_INC_DIR = os.path.join(LIBUV_DIR, 'include')
LIBUV_LIB_DIR = LIBUV_DIR



from cffi import FFI

ffi = FFI()
ffi.cdef("""

#define UV_VERSION_MAJOR ...
#define UV_VERSION_MINOR ...

enum uv_err_code_e {
  UV_UNKNOWN = -1,
  UV_OK = 0,
  UV_EOF,
  UV_EADDRINFO,
  UV_EACCES,
  UV_EAGAIN,
  UV_EADDRINUSE,
  UV_EADDRNOTAVAIL,
  UV_EAFNOSUPPORT,
  UV_EALREADY,
  UV_EBADF,
  UV_EBUSY,
  UV_ECONNABORTED,
  UV_ECONNREFUSED,
  UV_ECONNRESET,
  UV_EDESTADDRREQ,
  UV_EFAULT,
  UV_EHOSTUNREACH,
  UV_EINTR,
  UV_EINVAL,
  UV_EISCONN,
  UV_EMFILE,
  UV_EMSGSIZE,
  UV_ENETDOWN,
  UV_ENETUNREACH,
  UV_ENFILE,
  UV_ENOBUFS,
  UV_ENOMEM,
  UV_ENOTDIR,
  UV_EISDIR,
  UV_ENONET,
  UV_ENOTCONN,
  UV_ENOTSOCK,
  UV_ENOTSUP,
  UV_ENOENT,
  UV_ENOSYS,
  UV_EPIPE,
  UV_EPROTO,
  UV_EPROTONOSUPPORT,
  UV_EPROTOTYPE,
  UV_ETIMEDOUT,
  UV_ECHARSET,
  UV_EAIFAMNOSUPPORT,
  UV_EAISERVICE,
  UV_EAISOCKTYPE,
  UV_ESHUTDOWN,
  UV_EEXIST,
  UV_ESRCH,
  UV_ENAMETOOLONG,
  UV_EPERM,
  UV_ELOOP,
  UV_EXDEV,
  UV_ENOTEMPTY,
  UV_ENOSPC,
  UV_EIO,
  UV_EROFS,
  UV_ENODEV,
  UV_ESPIPE,
  UV_ECANCELED,
  ...
};

typedef enum uv_err_code_e uv_err_code;

typedef ... uv_handle_type;
typedef ... uv_req_type;

typedef ... uv_buf_t;
typedef ... uv_os_sock_t;
typedef ... uv_file;
typedef ... uv_mutex_t;
typedef ... uv_rwlock_t;
typedef ... uv_sem_t;
typedef ... uv_cond_t;
typedef ... uv_barrier_t;
typedef ... uv_thread_t;
typedef ... uv_once_t;
typedef ... uv_statbuf_t;
typedef ... uv_fs_type;
typedef ... uv_membership;

struct uv_err_s {
  ...;
};

struct uv_req_s {
  ...;
};

struct uv_shutdown_s {
  ...;
};

struct uv_handle_s {
  ...;
};

struct uv_stream_s {
  ...;
};

struct uv_write_s {
  ...;
};

struct uv_tcp_s {
  ...;
};

struct uv_connect_s {
  ...;
};

struct uv_udp_s {
  ...;
};

struct uv_udp_send_s {
  ...;
};

struct uv_tty_s {
  ...;
};

struct uv_pipe_s {
  ...;
};

struct uv_poll_s {
  ...;
};

struct uv_prepare_s {
  ...;
};

struct uv_check_s {
  ...;
};

struct uv_idle_s {
  ...;
};

struct uv_async_s {
  ...;
};

struct uv_timer_s {
  ...;
};

struct uv_getaddrinfo_s {
  ...;
};


struct uv_stdio_container_s {
  ...;
};

struct uv_process_options_s {
  ...;
};

struct uv_process_s {
  ...;
};

struct uv_work_s {
  ...;
};

struct uv_cpu_info_s {
  char* model;
  int speed;
  struct uv_cpu_times_s {
    uint64_t user;
    uint64_t nice;
    uint64_t sys;
    uint64_t idle;
    uint64_t irq;
  } cpu_times;
};

struct uv_interface_address_s {
  char* name;
  int is_internal;
  ...;
};

struct uv_fs_s {
  ...;
};

struct uv_fs_event_s {
  char* filename;
  ...;
};

struct uv_fs_poll_s {
  ...;
};

struct uv_signal_s {
  ...;
};

struct uv_loop_s {
  unsigned int active_handles;
  ...;
};

enum uv_fs_event {
  ...
};

enum uv_fs_event_flags {
  ...
};

enum uv_poll_event {
  UV_READABLE,
  UV_WRITABLE,
  ...
};

enum uv_udp_flags {
  ...
};

typedef ... uv_stdio_flags;

enum uv_process_flags {
  ...
};


typedef struct uv_loop_s uv_loop_t;
typedef struct uv_err_s uv_err_t;
typedef struct uv_handle_s uv_handle_t;
typedef struct uv_stream_s uv_stream_t;
typedef struct uv_tcp_s uv_tcp_t;
typedef struct uv_udp_s uv_udp_t;
typedef struct uv_pipe_s uv_pipe_t;
typedef struct uv_tty_s uv_tty_t;
typedef struct uv_poll_s uv_poll_t;
typedef struct uv_timer_s uv_timer_t;
typedef struct uv_prepare_s uv_prepare_t;
typedef struct uv_check_s uv_check_t;
typedef struct uv_idle_s uv_idle_t;
typedef struct uv_async_s uv_async_t;
typedef struct uv_process_s uv_process_t;
typedef struct uv_fs_event_s uv_fs_event_t;
typedef struct uv_fs_poll_s uv_fs_poll_t;
typedef struct uv_signal_s uv_signal_t;

typedef struct uv_req_s uv_req_t;
typedef struct uv_getaddrinfo_s uv_getaddrinfo_t;
typedef struct uv_shutdown_s uv_shutdown_t;
typedef struct uv_write_s uv_write_t;
typedef struct uv_connect_s uv_connect_t;
typedef struct uv_udp_send_s uv_udp_send_t;
typedef struct uv_fs_s uv_fs_t;
typedef struct uv_work_s uv_work_t;

typedef struct uv_stdio_container_s uv_stdio_container_t;
typedef struct uv_process_options_s uv_process_options_t;

typedef struct uv_cpu_info_s uv_cpu_info_t;
typedef struct uv_interface_address_s uv_interface_address_t;

/*******************/

uv_loop_t* uv_loop_new(void);
void uv_loop_delete(uv_loop_t*);
uv_loop_t* uv_default_loop(void);
int uv_run(uv_loop_t*);
int uv_run_once(uv_loop_t*);
void uv_ref(uv_handle_t*);
void uv_unref(uv_handle_t*);

void uv_update_time(uv_loop_t*);
int64_t uv_now(uv_loop_t*);

// note: we cannot use the original declaration: uv_buf_t is not fully defined
// typedef uv_buf_t (*uv_alloc_cb)(uv_handle_t* handle, size_t suggested_size);
// typedef void (*uv_read_cb)(uv_stream_t* stream, ssize_t nread, uv_buf_t buf);
// typedef void (*uv_read2_cb)(uv_pipe_t* pipe, ssize_t nread, uv_buf_t buf, uv_handle_type pending);

typedef void* uv_alloc_cb;
typedef void* uv_read_cb;
typedef void* uv_read2_cb;

typedef void (*uv_write_cb)(uv_write_t* req, int status);
typedef void (*uv_connect_cb)(uv_connect_t* req, int status);
typedef void (*uv_shutdown_cb)(uv_shutdown_t* req, int status);
typedef void (*uv_connection_cb)(uv_stream_t* server, int status);
typedef void (*uv_close_cb)(uv_handle_t* handle);
typedef void (*uv_poll_cb)(uv_poll_t* handle, int status, int events);
typedef void (*uv_timer_cb)(uv_timer_t* handle, int status);
typedef void (*uv_async_cb)(uv_async_t* handle, int status);
typedef void (*uv_prepare_cb)(uv_prepare_t* handle, int status);
typedef void (*uv_check_cb)(uv_check_t* handle, int status);
typedef void (*uv_idle_cb)(uv_idle_t* handle, int status);
typedef void (*uv_exit_cb)(uv_process_t*, int exit_status, int term_signal);
typedef void (*uv_walk_cb)(uv_handle_t* handle, void* arg);
typedef void (*uv_fs_cb)(uv_fs_t* req);
typedef void (*uv_work_cb)(uv_work_t* req);
typedef void (*uv_after_work_cb)(uv_work_t* req);
typedef void (*uv_getaddrinfo_cb)(uv_getaddrinfo_t* req, int status, struct addrinfo* res);
typedef void (*uv_fs_event_cb)(uv_fs_event_t* handle, const char* filename, int events, int status);
typedef void (*uv_fs_poll_cb)(uv_fs_poll_t* handle, int status, const uv_statbuf_t* prev, const uv_statbuf_t* curr);

typedef void (*uv_signal_cb)(uv_signal_t* handle, int signum);

uv_err_t uv_last_error(uv_loop_t*);
const char* uv_strerror(uv_err_t err);
const char* uv_err_name(uv_err_t err);

int uv_shutdown(uv_shutdown_t* req, uv_stream_t* handle, uv_shutdown_cb cb);

size_t uv_handle_size(uv_handle_type type);
size_t uv_req_size(uv_req_type type);
int uv_is_active(const uv_handle_t* handle);
void uv_walk(uv_loop_t* loop, uv_walk_cb walk_cb, void* arg);
void uv_close(uv_handle_t* handle, uv_close_cb close_cb);

uv_buf_t uv_buf_init(char* base, unsigned int len);
size_t uv_strlcpy(char* dst, const char* src, size_t size);
size_t uv_strlcat(char* dst, const char* src, size_t size);

int uv_listen(uv_stream_t* stream, int backlog, uv_connection_cb cb);
int uv_accept(uv_stream_t* server, uv_stream_t* client);
int uv_read_start(uv_stream_t*, uv_alloc_cb alloc_cb, uv_read_cb read_cb);

int uv_read_stop(uv_stream_t*);
int uv_read2_start(uv_stream_t*, uv_alloc_cb alloc_cb, uv_read2_cb read_cb);
int uv_write(uv_write_t* req, uv_stream_t* handle, uv_buf_t bufs[], int bufcnt, uv_write_cb cb);
int uv_write2(uv_write_t* req, uv_stream_t* handle, uv_buf_t bufs[], int bufcnt, uv_stream_t* send_handle, uv_write_cb cb);

int uv_is_readable(const uv_stream_t* handle);
int uv_is_writable(const uv_stream_t* handle);
int uv_is_closing(const uv_handle_t* handle);

int uv_tcp_init(uv_loop_t*, uv_tcp_t* handle);
int uv_tcp_open(uv_tcp_t* handle, uv_os_sock_t sock);
int uv_tcp_nodelay(uv_tcp_t* handle, int enable);
int uv_tcp_keepalive(uv_tcp_t* handle, int enable, unsigned int delay);
int uv_tcp_simultaneous_accepts(uv_tcp_t* handle, int enable);
int uv_tcp_bind(uv_tcp_t* handle, struct sockaddr_in);
int uv_tcp_bind6(uv_tcp_t* handle, struct sockaddr_in6);
int uv_tcp_getsockname(uv_tcp_t* handle, struct sockaddr* name, int* namelen);
int uv_tcp_getpeername(uv_tcp_t* handle, struct sockaddr* name, int* namelen);
int uv_tcp_connect(uv_connect_t* req, uv_tcp_t* handle, struct sockaddr_in address, uv_connect_cb cb);
int uv_tcp_connect6(uv_connect_t* req, uv_tcp_t* handle, struct sockaddr_in6 address, uv_connect_cb cb);

typedef void (*uv_udp_send_cb)(uv_udp_send_t* req, int status);

// note: we cannot use the original declaration: uv_buf_t is not fully defined
//typedef void (*uv_udp_recv_cb)(uv_udp_t* handle, ssize_t nread, uv_buf_t buf, struct sockaddr* addr, unsigned flags);
typedef void *uv_udp_recv_cb;

int uv_udp_init(uv_loop_t*, uv_udp_t* handle);
int uv_udp_open(uv_udp_t* handle, uv_os_sock_t sock);
int uv_udp_bind(uv_udp_t* handle, struct sockaddr_in addr, unsigned flags);
int uv_udp_bind6(uv_udp_t* handle, struct sockaddr_in6 addr, unsigned flags);
int uv_udp_getsockname(uv_udp_t* handle, struct sockaddr* name, int* namelen);
int uv_udp_set_membership(uv_udp_t* handle, const char* multicast_addr, const char* interface_addr, uv_membership membership);
int uv_udp_set_multicast_loop(uv_udp_t* handle, int on);
int uv_udp_set_multicast_ttl(uv_udp_t* handle, int ttl);
int uv_udp_set_broadcast(uv_udp_t* handle, int on);
int uv_udp_set_ttl(uv_udp_t* handle, int ttl);
int uv_udp_send(uv_udp_send_t* req, uv_udp_t* handle, uv_buf_t bufs[], int bufcnt, struct sockaddr_in addr, uv_udp_send_cb send_cb);
int uv_udp_send6(uv_udp_send_t* req, uv_udp_t* handle, uv_buf_t bufs[], int bufcnt, struct sockaddr_in6 addr, uv_udp_send_cb send_cb);
int uv_udp_recv_start(uv_udp_t* handle, uv_alloc_cb alloc_cb, uv_udp_recv_cb recv_cb);
int uv_udp_recv_stop(uv_udp_t* handle);

int uv_tty_init(uv_loop_t*, uv_tty_t*, uv_file fd, int readable);
int uv_tty_set_mode(uv_tty_t*, int mode);
void uv_tty_reset_mode(void);
int uv_tty_get_winsize(uv_tty_t*, int* width, int* height);
uv_handle_type uv_guess_handle(uv_file file);

int uv_pipe_init(uv_loop_t*, uv_pipe_t* handle, int ipc);
int uv_pipe_open(uv_pipe_t*, uv_file file);
int uv_pipe_bind(uv_pipe_t* handle, const char* name);
void uv_pipe_connect(uv_connect_t* req, uv_pipe_t* handle, const char* name, uv_connect_cb cb);
void uv_pipe_pending_instances(uv_pipe_t* handle, int count);

int uv_poll_init(uv_loop_t* loop, uv_poll_t* handle, int fd);
int uv_poll_init_socket(uv_loop_t* loop, uv_poll_t* handle, uv_os_sock_t socket);
int uv_poll_start(uv_poll_t* handle, int events, uv_poll_cb cb);
int uv_poll_stop(uv_poll_t* handle);

int uv_prepare_init(uv_loop_t*, uv_prepare_t* prepare);
int uv_prepare_start(uv_prepare_t* prepare, uv_prepare_cb cb);
int uv_prepare_stop(uv_prepare_t* prepare);

int uv_check_init(uv_loop_t*, uv_check_t* check);
int uv_check_start(uv_check_t* check, uv_check_cb cb);
int uv_check_stop(uv_check_t* check);

int uv_idle_init(uv_loop_t*, uv_idle_t* idle);
int uv_idle_start(uv_idle_t* idle, uv_idle_cb cb);
int uv_idle_stop(uv_idle_t* idle);

int uv_async_init(uv_loop_t*, uv_async_t* async, uv_async_cb async_cb);
int uv_async_send(uv_async_t* async);

int uv_timer_init(uv_loop_t*, uv_timer_t* timer);
int uv_timer_start(uv_timer_t* timer, uv_timer_cb cb, int64_t timeout, int64_t repeat);
int uv_timer_stop(uv_timer_t* timer);
int uv_timer_again(uv_timer_t* timer);
void uv_timer_set_repeat(uv_timer_t* timer, int64_t repeat);
int64_t uv_timer_get_repeat(uv_timer_t* timer);

int uv_getaddrinfo(uv_loop_t* loop, uv_getaddrinfo_t* req, uv_getaddrinfo_cb getaddrinfo_cb, const char* node, const char* service, const struct addrinfo* hints);
void uv_freeaddrinfo(struct addrinfo* ai);

int uv_spawn(uv_loop_t*, uv_process_t*, uv_process_options_t options);
int uv_process_kill(uv_process_t*, int signum);
uv_err_t uv_kill(int pid, int signum);
int uv_queue_work(uv_loop_t* loop, uv_work_t* req, uv_work_cb work_cb, uv_after_work_cb after_work_cb);

char** uv_setup_args(int argc, char** argv);
uv_err_t uv_get_process_title(char* buffer, size_t size);
uv_err_t uv_set_process_title(const char* title);
uv_err_t uv_resident_set_memory(size_t* rss);
uv_err_t uv_uptime(double* uptime);

uv_err_t uv_cpu_info(uv_cpu_info_t** cpu_infos, int* count);
void uv_free_cpu_info(uv_cpu_info_t* cpu_infos, int count);

uv_err_t uv_interface_addresses(uv_interface_address_t** addresses, int* count);
void uv_free_interface_addresses(uv_interface_address_t* addresses, int count);

void uv_fs_req_cleanup(uv_fs_t* req);
int uv_fs_close(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_fs_cb cb);
int uv_fs_stat(uv_loop_t* loop, uv_fs_t* req, const char* path, uv_fs_cb cb);
int uv_fs_fstat(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_fs_cb cb);
int uv_fs_rename(uv_loop_t* loop, uv_fs_t* req, const char* path, const char* new_path, uv_fs_cb cb);
int uv_fs_fsync(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_fs_cb cb);
int uv_fs_fdatasync(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_fs_cb cb);
int uv_fs_ftruncate(uv_loop_t* loop, uv_fs_t* req, uv_file file, int64_t offset, uv_fs_cb cb);
int uv_fs_sendfile(uv_loop_t* loop, uv_fs_t* req, uv_file out_fd, uv_file in_fd, int64_t in_offset, size_t length, uv_fs_cb cb);
int uv_fs_chmod(uv_loop_t* loop, uv_fs_t* req, const char* path, int mode, uv_fs_cb cb);
int uv_fs_utime(uv_loop_t* loop, uv_fs_t* req, const char* path, double atime, double mtime, uv_fs_cb cb);
int uv_fs_futime(uv_loop_t* loop, uv_fs_t* req, uv_file file, double atime, double mtime, uv_fs_cb cb);
int uv_fs_lstat(uv_loop_t* loop, uv_fs_t* req, const char* path, uv_fs_cb cb);
int uv_fs_link(uv_loop_t* loop, uv_fs_t* req, const char* path, const char* new_path, uv_fs_cb cb);

#define UV_FS_SYMLINK_DIR          ...
#define UV_FS_SYMLINK_JUNCTION     ...

int uv_fs_symlink(uv_loop_t* loop, uv_fs_t* req, const char* path, const char* new_path, int flags, uv_fs_cb cb);
int uv_fs_readlink(uv_loop_t* loop, uv_fs_t* req, const char* path, uv_fs_cb cb);
int uv_fs_fchmod(uv_loop_t* loop, uv_fs_t* req, uv_file file, int mode, uv_fs_cb cb);
int uv_fs_chown(uv_loop_t* loop, uv_fs_t* req, const char* path, int uid, int gid, uv_fs_cb cb);
int uv_fs_fchown(uv_loop_t* loop, uv_fs_t* req, uv_file file, int uid, int gid, uv_fs_cb cb);

int uv_fs_poll_init(uv_loop_t* loop, uv_fs_poll_t* handle);
int uv_fs_poll_start(uv_fs_poll_t* handle, uv_fs_poll_cb poll_cb, const char* path, unsigned int interval);
int uv_fs_poll_stop(uv_fs_poll_t* handle);

int uv_signal_init(uv_loop_t* loop, uv_signal_t* handle);
int uv_signal_start(uv_signal_t* handle, uv_signal_cb signal_cb, int signum);
int uv_signal_stop(uv_signal_t* handle);

void uv_loadavg(double avg[3]);

int uv_fs_event_init(uv_loop_t* loop, uv_fs_event_t* handle, const char* filename, uv_fs_event_cb cb, int flags);

struct sockaddr_in uv_ip4_addr(const char* ip, int port);
struct sockaddr_in6 uv_ip6_addr(const char* ip, int port);

int uv_ip4_name(struct sockaddr_in* src, char* dst, size_t size);
int uv_ip6_name(struct sockaddr_in6* src, char* dst, size_t size);

uv_err_t uv_inet_ntop(int af, const void* src, char* dst, size_t size);
uv_err_t uv_inet_pton(int af, const char* src, void* dst);

int uv_exepath(char* buffer, size_t* size);

uv_err_t uv_cwd(char* buffer, size_t size);
uv_err_t uv_chdir(const char* dir);

uint64_t uv_get_free_memory(void);
uint64_t uv_get_total_memory(void);

uint64_t uv_hrtime(void);

int uv_mutex_init(uv_mutex_t* handle);
void uv_mutex_destroy(uv_mutex_t* handle);
void uv_mutex_lock(uv_mutex_t* handle);
int uv_mutex_trylock(uv_mutex_t* handle);
void uv_mutex_unlock(uv_mutex_t* handle);

int uv_rwlock_init(uv_rwlock_t* rwlock);
void uv_rwlock_destroy(uv_rwlock_t* rwlock);
void uv_rwlock_rdlock(uv_rwlock_t* rwlock);
int uv_rwlock_tryrdlock(uv_rwlock_t* rwlock);
void uv_rwlock_rdunlock(uv_rwlock_t* rwlock);
void uv_rwlock_wrlock(uv_rwlock_t* rwlock);
int uv_rwlock_trywrlock(uv_rwlock_t* rwlock);
void uv_rwlock_wrunlock(uv_rwlock_t* rwlock);

int uv_sem_init(uv_sem_t* sem, unsigned int value);
void uv_sem_destroy(uv_sem_t* sem);
void uv_sem_post(uv_sem_t* sem);
void uv_sem_wait(uv_sem_t* sem);
int uv_sem_trywait(uv_sem_t* sem);

int uv_cond_init(uv_cond_t* cond);
void uv_cond_destroy(uv_cond_t* cond);
void uv_cond_signal(uv_cond_t* cond);
void uv_cond_broadcast(uv_cond_t* cond);
int uv_cond_timedwait(uv_cond_t* cond, uv_mutex_t* mutex, uint64_t timeout);

int uv_barrier_init(uv_barrier_t* barrier, unsigned int count);
void uv_barrier_destroy(uv_barrier_t* barrier);
void uv_barrier_wait(uv_barrier_t* barrier);

void uv_once(uv_once_t* guard, void *callback);

int uv_thread_create(uv_thread_t *tid, void *entry, void *arg);
unsigned long uv_thread_self(void);
int uv_thread_join(uv_thread_t *tid);
""")


# check if we need any extra libraries...
extra_compile_args = []
extra_link_args = []
if sys.platform in ['linux', 'linux2']:
    extra_link_args.append('-lrt')
if sys.platform in ['darwin']:
    extra_link_args.append('-framework CoreServices')


libuv = C = ffi.verify("""
#include <uv.h>
""",
    include_dirs = [LIBUV_INC_DIR],
    extra_compile_args = extra_compile_args,
    libraries = ["uv"],
    library_dirs = [LIBUV_LIB_DIR],
    ext_package = 'evy.uv',                   # must match the package defined in setup.py
    extra_link_args = extra_link_args)


def get_version():
    return 'libuv-%d.%02d' % (libuv.UV_VERSION_MAJOR, libuv.UV_VERSION_MINOR)
