from __future__ import absolute_import
import sys, os, traceback, signal as signalmodule

__all__ = ['get_version',
           'get_header_version',
           'supported_backends',
           'recommended_backends',
           'embeddable_backends',
           'time',
           'loop']

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

typedef uv_buf_t (*uv_alloc_cb)(uv_handle_t* handle, size_t suggested_size);
typedef void (*uv_read_cb)(uv_stream_t* stream, ssize_t nread, uv_buf_t buf);
typedef void (*uv_read2_cb)(uv_pipe_t* pipe, ssize_t nread, uv_buf_t buf, uv_handle_type pending);

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

enum uv_udp_flags {
  UV_UDP_IPV6ONLY,
  UV_UDP_PARTIAL,
  ...
};

typedef void (*uv_udp_send_cb)(uv_udp_send_t* req, int status);
typedef void (*uv_udp_recv_cb)(uv_udp_t* handle, ssize_t nread, uv_buf_t buf, struct sockaddr* addr, unsigned flags);

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

enum uv_poll_event {
  UV_READABLE,
  UV_WRITABLE,
  ...
};

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

/* uv_spawn() options */
typedef enum {
  UV_IGNORE,
  UV_CREATE_PIPE,
  UV_INHERIT_FD,
  UV_INHERIT_STREAM,
  UV_READABLE_PIPE,
  UV_WRITABLE_PIPE,
  ...
} uv_stdio_flags;

enum uv_process_flags {
  UV_PROCESS_SETUID,
  UV_PROCESS_SETGID,
  UV_PROCESS_WINDOWS_VERBATIM_ARGUMENTS,
  UV_PROCESS_DETACHED,
  ...
};


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

typedef enum {
  UV_FS_UNKNOWN,
  UV_FS_CUSTOM,
  UV_FS_OPEN,
  UV_FS_CLOSE,
  UV_FS_READ,
  UV_FS_WRITE,
  UV_FS_SENDFILE,
  UV_FS_STAT,
  UV_FS_LSTAT,
  UV_FS_FSTAT,
  UV_FS_FTRUNCATE,
  UV_FS_UTIME,
  UV_FS_FUTIME,
  UV_FS_CHMOD,
  UV_FS_FCHMOD,
  UV_FS_FSYNC,
  UV_FS_FDATASYNC,
  UV_FS_UNLINK,
  UV_FS_RMDIR,
  UV_FS_MKDIR,
  UV_FS_RENAME,
  UV_FS_READDIR,
  UV_FS_LINK,
  UV_FS_SYMLINK,
  UV_FS_READLINK,
  UV_FS_CHOWN,
  UV_FS_FCHOWN,
  ...
} uv_fs_type;


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


enum uv_fs_event {
  UV_RENAME,
  UV_CHANGE,
  ...
};


int uv_fs_poll_init(uv_loop_t* loop, uv_fs_poll_t* handle);
int uv_fs_poll_start(uv_fs_poll_t* handle, uv_fs_poll_cb poll_cb, const char* path, unsigned int interval);
int uv_fs_poll_stop(uv_fs_poll_t* handle);


/* These functions are no-ops on Windows. */
int uv_signal_init(uv_loop_t* loop, uv_signal_t* handle);
int uv_signal_start(uv_signal_t* handle, uv_signal_cb signal_cb, int signum);
int uv_signal_stop(uv_signal_t* handle);

void uv_loadavg(double avg[3]);

enum uv_fs_event_flags {
  UV_FS_EVENT_WATCH_ENTRY,
  UV_FS_EVENT_STAT,
  UV_FS_EVENT_RECURSIVE,
  ...
};


int uv_fs_event_init(uv_loop_t* loop, uv_fs_event_t* handle, const char* filename, uv_fs_event_cb cb, int flags);

/* Utility */

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



libuv = C = ffi.verify("""
#include <uv.h>
""",
    include_dirs = [LIBUV_INC_DIR],
    libraries = ["uv"],
    library_dirs = [LIBUV_LIB_DIR],
    ext_package = 'libuv',
    extra_link_args = ['-lrt'])



def get_header_version():
    return 'libuv-%d.%02d' % (libuv.UV_VERSION_MAJOR, libuv.UV_VERSION_MINOR)


####################################################################################################


class Loop(object):
    """
    A main loop
    """

    error_handler = None

    def __init__(self, flags=None, default=True, ptr=0):
        sys.stderr.write("*** using uv loop\n")
        self._signal_checker = ffi.new("uv_prepare_t *")
        self._signal_checker_cb = ffi.callback("void(*)(uv_loop_t *, uv_prepare_t *, int)", before_block)
        libuv.uv_prepare_init(self._signal_checker, self._signal_checker_cb)

        # #ifdef _WIN32
        #         libuv.uv_timer_init(&self._periodic_signal_checker, <void*>gevent_periodic_signal_check, 0.3, 0.3)
        # #endif

        if ptr:
            assert ffi.typeof(ptr) is ffi.typeof("uv_loop_t *")
            self._ptr = ptr
        else:
            if _default_loop_destroyed:
                default = False
            if default:
                self._ptr = libuv.uv_default_loop()
                if not self._ptr:
                    raise SystemError("uv_default_loop() failed")
                libuv.uv_prepare_start(self._ptr, self._signal_checker)
                libuv.uv_unref(self._ptr)

                # if sys.platform == "win32":
                #     libuv.uv_timer_start(self._ptr, &self._periodic_signal_checker)
                #     libuv.uv_unref(self._ptr)

            else:
                self._ptr = libuv.uv_loop_new()
                if not self._ptr:
                    raise SystemError("uv_loop_new() failed")
                
            #if default or __SYSERR_CALLBACK is None:
            #    set_syserr_cb(self._handle_syserr)

    def _stop_signal_checker(self):
        if libuv.uv_is_active(self._signal_checker):
            libuv.uv_ref(self._ptr)
            libuv.uv_prepare_stop(self._ptr, self._signal_checker)
        # #ifdef _WIN32
        #         if libuv.uv_is_active(&self._periodic_signal_checker):
        #             libuv.uv_ref(self._ptr)
        #             libuv.uv_timer_stop(self._ptr, &self._periodic_signal_checker)
        # #endif

    def destroy(self):
        global _default_loop_destroyed
        if self._ptr:
            self._stop_signal_checker()
            #if __SYSERR_CALLBACK == self._handle_syserr:
            #    set_syserr_cb(None)
            if libuv.uv_is_default_loop(self._ptr):
                _default_loop_destroyed = True
            libuv.uv_loop_destroy(self._ptr)
            self._ptr = ffi.NULL

    @property
    def ptr(self):
        return self._ptr

    @property
    def WatcherType(self):
        return Watcher

    def _handle_syserr(self, message, errno):
        self.handle_error(None, SystemError, SystemError(message + ': ' + os.strerror(errno)), None)

    def handle_error(self, context, type, value, tb):
        handle_error = None
        error_handler = self.error_handler
        if error_handler is not None:
            # we do want to do getattr every time so that setting Hub.handle_error property just works
            handle_error = getattr(error_handler, 'handle_error', error_handler)
            handle_error(context, type, value, tb)
        else:
            self._default_handle_error(context, type, value, tb)

    def _default_handle_error(self, context, type, value, tb):
        # note: Hub sets its own error handler so this is not used by gevent
        # this is here to make core.loop usable without the rest of gevent
        traceback.print_exception(type, value, tb)
        #libuv.uv_break(self._ptr, libuv.EVBREAK_ONE)
        raise NotImplementedError()

    def run(self, once=False):
        if once:
            libuv.uv_run_once(self._ptr)
        else:
            libuv.uv_run(self._ptr)

    def ref(self):
        libuv.uv_ref(self._ptr)

    def unref(self):
        libuv.uv_unref(self._ptr)

    def now(self):
        return libuv.uv_now(self._ptr)

    def XXX__repr__(self):
        return '<%s at 0x%x %s>' % (self.__class__.__name__, id(self), self._format())

    @property
    def default_loop(self):
        return libuv.uv_default_loop()

    def io(self, fd, events, ref=True):
        return Poll(self, fd, events, ref)

    def timer(self, after, repeat=0.0, ref=True):
        return Timer(self, after, repeat, ref)

    def signal(self, signum, ref=True):
        return Signal(self, signum, ref)

    def idle(self, ref=True):
        return Idle(self, ref)

    def prepare(self, ref=True):
        return Prepare(self, ref)

    def async(self, ref=True):
        return Async(self, ref)

    def callback(self):
        return Callback(self)

    def run_callback(self, func, *args, **kw):
        result = Callback(self)
        result.start(func, *args)
        return result

    def _format(self):
        msg = self.backend
        if self.default:
            msg += ' default'
        return msg

    def fileno(self):
        fd = self._ptr.backend_fd
        if fd >= 0:
            return fd


####################################################################################################


class Watcher(object):
    """
    An general watcher
    """
    libuv_start_this_watcher = None
    libuv_stop_this_watcher = None

    _callback = None
    loop = None
    args = None
    _flags = 0

    def __init__(self, _loop, ref=True):
        assert isinstance(_loop, Loop)
        assert self.libuv_stop_this_watcher is not None
        self.loop = _loop
        if ref:
            self._flags = 0
        else:
            self._flags = 4

    def _run_callback(self, loop, c_watcher, revents):
        try:
            self.callback(*self.args)
        except:
            try:
                self.loop.handle_error(self, *sys.exc_info())
            finally:
                if revents & (libuv.UV_READABLE | libuv.UV_WRITABLE):
                    # /* poll watcher: not stopping it may cause the failing callback to be called repeatedly */
                    try:
                        self.stop()
                    except:
                        self.loop.handle_error(self, *sys.exc_info())
                    return

        # callbacks' self.active differs from uv_is_active(...) at
        # this point. don't use it!
        if not libuv.uv_is_active(c_watcher):
            self.stop()

    def _libuv_unref(self):
        if self._flags & 6 == 4:
            libuv.uv_unref(self.loop._ptr)
            self._flags |= 2

    def _python_incref(self):
        if not self._flags & 1:
            # Py_INCREF(<PyObjectPtr>self)
            self._flags |= 1

    def _get_ref(self):
        return False if self._flags & 4 else True

    def _set_ref(self, value):
        if value:
            if not self._flags & 4:
                return  # ref is already True
            if self._flags & 2:  # uv_unref was called, undo
                libuv.uv_ref(self.loop._ptr)
            self._flags &= ~6  # do not want unref, no outstanding unref
        else:
            if self._flags & 4:
                return  # ref is already False
            self._flags |= 4
            if not self._flags & 2 and libuv.uv_is_active(self._watcher):
                libuv.uv_unref(self.loop._ptr)
                self._flags |= 2

    ref = property(_get_ref, _set_ref)

    def _get_callback(self):
        return self._callback

    def _set_callback(self, callback):
        assert callable(callback)
        self._callback = callback
    callback = property(_get_callback, _set_callback)

    def start(self, callback, *args):
        self.callback = callback
        self.args = args
        self._libuv_unref()
        self.libuv_start_this_watcher(self.loop._ptr, self._watcher)
        self._python_incref()

    def stop(self):
        if self._flags & 2:
            libuv.uv_ref(self.loop._ptr)
            self._flags &= ~2
        self.libuv_stop_this_watcher(self.loop._ptr, self._watcher)
        self._callback = None
        self.args = None
        if self._flags & 1:
            # Py_DECREF(<PyObjectPtr>self)
            self._flags &= ~1

    def feed(self, revents, callback, *args):
        self.callback = callback
        self.args = args
        if self._flags & 6 == 4:
            libuv.uv_unref(self.loop._ptr)
            self._flags |= 2
        libuv.uv_feed_event(self.loop._ptr, self._watcher, revents)
        if not self._flags & 1:
            # Py_INCREF(<PyObjectPtr>self)
            self._flags |= 1

    @property
    def active(self):
        return True if libuv.uv_is_active(self._watcher) else False

    @property
    def pending(self):
        return True if libuv.uv_is_pending(self._watcher) else False



class Poll(Watcher):
    """
    This watcher is used to watch file descriptors for readability and writability, similar to the
    purpose of poll(2).

    The purpose is to enable integrating external libraries that rely on the event loop to signal
    it about the socket status changes, like c-ares or libssh2. Using Poll for any other other
    purpose is not recommended; uv_tcp_t, uv_udp_t, etc. provide an implementation that is much
    faster and more scalable than what can be achieved with uv_poll_t, especially on Windows.

    It is possible that Poll occasionally signals that a file descriptor is readable or writable
    even when it isn't. The user should therefore always be prepared to handle EAGAIN or equivalent
    when it attempts to read from or write to the fd.

    It is not okay to have multiple active Poll watchers for the same socket. This can cause
    libuv to busyloop or otherwise malfunction.

    The user should not close a file descriptor while it is being polled by an active Poll watcher.
    This can cause the poll watcher to report an error, but it might also start polling another socket.
    However the fd can be safely closed immediately after a call to uv_poll_stop() or uv_close().

    On windows only sockets can be polled with uv_poll. On unix any file
    descriptor that would be accepted by poll(2) can be used with uv_poll.
    """
    libuv_start_this_watcher = libuv.uv_poll_start
    libuv_stop_this_watcher = libuv.uv_poll_stop

    def __init__(self, loop, fd, events, ref=True):
        if fd < 0:
            raise ValueError('fd must be non-negative: %r' % fd)

        if events & ~(libuv.UV_READABLE | libuv.UV_WRITABLE):
            raise ValueError('illegal event mask: %r' % events)

        self._watcher = ffi.new("uv_poll_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_poll_t *, int)", self._run_callback)

        libuv.uv_poll_init(self._watcher, self._cb, fd, events)
        Watcher.__init__(self, loop, ref=ref)

    def _get_fd(self):
        return self._watcher.fd

    def _set_fd(self, fd):
        if libuv.uv_is_active(self._watcher):
            raise AttributeError("'poll' watcher attribute 'fd' is read-only while watcher is active")
        libuv.uv_poll_init(self._watcher, self._cb, fd, self._watcher.events)

    fd = property(_get_fd, _set_fd)

    def _get_events(self):
        return self._watcher.fd

    def _set_events(self, events):
        if libuv.uv_is_active(self._watcher):
            raise AttributeError("'poll' watcher attribute 'events' is read-only while watcher is active")
        libuv.uv_poll_init(self._watcher, self._cb, self._watcher.fd, events)

    events = property(_get_events, _set_events)

    def _format(self):
        return ' fd=%s events=%s' % (self.fd, self.events_str)



class Timer(Watcher):
    """
    Start a timer. `timeout` and `repeat` are in milliseconds.

    If timeout is zero, the callback fires on the next tick of the event loop.

    If repeat is non-zero, the callback fires first after timeout milliseconds and then repeatedly
    after repeat milliseconds.

    timeout and repeat are signed integers but that will change in a future version of libuv. Don't
    pass in negative values, you'll get a nasty surprise when that change becomes effective.
    """
    libuv_start_this_watcher = libuv.uv_timer_start
    libuv_stop_this_watcher = libuv.uv_timer_stop

    def __init__(self, loop, after=0.0, repeat=0.0, ref=True):
        if repeat < 0.0:
            raise ValueError("repeat must be positive or zero: %r" % repeat)

        self._watcher = ffi.new("uv_timer_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_timer_t *, int)", self._run_callback)

        libuv.uv_timer_init(self._watcher, self._cb, after, repeat)
        Watcher.__init__(self, loop, ref=ref)

    def start(self, callback, *args, **kw):
        update = kw.get("update", True)
        self.callback = callback
        self.args = args

        self._libuv_unref()  # LIBEV_UNREF

        if update:
            libuv.uv_update_time(self.loop._ptr)

        libuv.uv_timer_start(self.loop._ptr, self._watcher)

        self._python_incref()  # PYTHON_INCREF

    @property
    def at(self):
        return self._watcher.at

    def again(self, callback, *args, **kw):
        update = kw.get("update", True)
        self.callback = callback
        self.args = args
        self._libuv_unref()
        if update:
            libuv.uv_now_update(self.loop._ptr)
        libuv.uv_timer_again(self.loop._ptr, self._watcher)
        self._python_incref()


class Signal(Watcher):
    """
    UNIX signal handling on a per-event loop basis. The implementation is not
    ultra efficient so don't go creating a million event loops with a million
    signal watchers.

    Some signal support is available on Windows:

      SIGINT is normally delivered when the user presses CTRL+C. However, like
      on Unix, it is not generated when terminal raw mode is enabled.

      SIGBREAK is delivered when the user pressed CTRL+BREAK.

      SIGHUP is generated when the user closes the console window. On SIGHUP the
      program is given approximately 10 seconds to perform cleanup. After that
      Windows will unconditionally terminate it.

      SIGWINCH is raised whenever libuv detects that the console has been
      resized. SIGWINCH is emulated by libuv when the program uses an uv_tty_t
      handle to write to the console. SIGWINCH may not always be delivered in a
      timely manner; libuv will only detect size changes when the cursor is
      being moved. When a readable uv_tty_handle is used in raw mode, resizing
      the console buffer will also trigger a SIGWINCH signal.

    Watchers for other signals can be successfully created, but these signals
    are never generated. These signals are: SIGILL, SIGABRT, SIGFPE, SIGSEGV,
    SIGTERM and SIGKILL.

    Note that calls to raise() or abort() to programmatically raise a signal are
    not detected by libuv; these will not trigger a signal watcher.

    """
    libuv_start_this_watcher = libuv.uv_signal_start
    libuv_stop_this_watcher = libuv.uv_signal_stop

    def __init__(self, loop, signalnum, ref=True):
        if signalnum < 1 or signalnum >= signalmodule.NSIG:
            raise ValueError('illegal signal number: %r' % signalnum)
            # still possible to crash on one of libuv's asserts:
        # 1) "libuv: uv_signal_start called with illegal signal number"
        #    EV_NSIG might be different from signal.NSIG on some platforms
        # 2) "libuv: a signal must not be attached to two different loops"
        #    we probably could check that in LIBEV_EMBED mode, but not in general

        self._watcher = ffi.new("uv_signal_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_signal_t *, int)", self._run_callback)

        libuv.uv_signal_init(self._watcher, self._cb, signalnum)
        Watcher.__init__(self, loop, ref=ref)


class Idle(Watcher):
    """
    Every active idle handle gets its callback called repeatedly until it is stopped. This happens
    after all other types of callbacks are processed. When there are multiple "idle" handles active,
    their callbacks are called in turn.
    """
    libuv_start_this_watcher = libuv.uv_idle_start
    libuv_stop_this_watcher = libuv.uv_idle_stop

    def __init__(self, loop, ref=True):
        self._watcher = ffi.new("uv_idle_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_idle_t *, int)", self._run_callback)
        libuv.uv_idle_init(self._watcher, self._cb)
        Watcher.__init__(self, loop, ref=ref)


class Prepare(Watcher):
    """
    Every active prepare handle gets its callback called exactly once per loop iteration, just before
    the system blocks to wait for completed i/o.
    """
    libuv_start_this_watcher = libuv.uv_prepare_start
    libuv_stop_this_watcher = libuv.uv_prepare_stop

    def __init__(self, loop, ref=True):
        self._watcher = ffi.new("uv_prepare_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_prepare_t *, int)", self._run_callback)
        libuv.uv_prepare_init(self._watcher, self._cb)
        Watcher.__init__(self, loop, ref=ref)


class Async(Watcher):
    """
    An Async wakes up the event loop and calls the async handle's callback.
    There is no guarantee that every send() call leads to exactly one invocation of the
    callback; the only guarantee is that the callback function is called at least once after the
    call send(). Unlike all other libuv functions, send() can be called from
    another thread.
    """
    libuv_start_this_watcher = libuv.uv_async_start
    libuv_stop_this_watcher = libuv.uv_async_stop

    def __init__(self, loop, ref=True):
        self._watcher = ffi.new("uv_async_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_async_t *, int)", self._run_callback)
        libuv.uv_async_init(self._watcher, self._cb)
        Watcher.__init__(self, loop, ref=ref)

    def send(self):
        libuv.uv_async_send(self.loop._ptr, self._watcher)

    @property
    def pending(self):
        return True if libuv.uv_async_pending(self._watcher) else False



class Callback(Watcher):
    """
    Pseudo-watcher used to execute a callback in the loop as soon as possible.
    """

    # does not matter which type we actually use, since we are going
    # to feed() events, not start watchers

    libuv_start_this_watcher = libuv.uv_prepare_start
    libuv_stop_this_watcher = libuv.uv_prepare_stop

    def __init__(self, loop, ref=True):
        self._watcher = ffi.new("uv_prepare_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_prepare_t *, int)", self._run_callback)
        libuv.uv_prepare_init(self._watcher, self._cb)
        Watcher.__init__(self, loop, ref=ref)

    def start(self, callback, *args):
        self.callback = callback
        self.args = args
        libuv.uv_feed_event(self.loop._ptr, self._watcher, libuv.EV_CUSTOM)
        self._python_incref()

    @property
    def active(self):
        return self.callback is not None


