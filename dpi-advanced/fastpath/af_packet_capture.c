/*
 * RansomEye DPI Advanced - AF_PACKET Capture
 * AUTHORITATIVE: AF_PACKET capture backend for DPI runtime
 *
 * NOTE:
 * - This implementation is intentionally minimal and deterministic.
 * - It provides a C-backed capture path used by the DPI runtime via ctypes.
 * - It does not use PACKET_MMAP to keep runtime complexity bounded.
 */

#include <linux/if_packet.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <stdint.h>
#include <time.h>

/*
 * Initialize AF_PACKET socket
 * Returns socket fd on success, -1 on error.
 */
int af_packet_open(const char *interface) {
    int sockfd;
    struct sockaddr_ll sll;
    struct ifreq ifr;
    
    // Create AF_PACKET socket
    sockfd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    if (sockfd < 0) {
        return -1;
    }
    
    // Get interface index
    strncpy(ifr.ifr_name, interface, IFNAMSIZ);
    if (ioctl(sockfd, SIOCGIFINDEX, &ifr) < 0) {
        close(sockfd);
        return -1;
    }
    
    // Bind to interface
    memset(&sll, 0, sizeof(sll));
    sll.sll_family = AF_PACKET;
    sll.sll_ifindex = ifr.ifr_ifindex;
    sll.sll_protocol = htons(ETH_P_ALL);
    
    if (bind(sockfd, (struct sockaddr *)&sll, sizeof(sll)) < 0) {
        close(sockfd);
        return -1;
    }
    return sockfd;
}

/*
 * Read a single packet into buffer.
 * Returns 0 on success, -1 on error.
 */
int af_packet_read(int sockfd, unsigned char *buffer, int buffer_len, int *out_len, long *out_sec, long *out_nsec) {
    if (!buffer || buffer_len <= 0 || !out_len) {
        return -1;
    }

    struct timespec ts;
    ssize_t received = recvfrom(sockfd, buffer, (size_t)buffer_len, 0, NULL, NULL);
    if (received < 0) {
        return -1;
    }

    if (clock_gettime(CLOCK_REALTIME, &ts) == 0) {
        if (out_sec) {
            *out_sec = (long)ts.tv_sec;
        }
        if (out_nsec) {
            *out_nsec = (long)ts.tv_nsec;
        }
    } else {
        if (out_sec) {
            *out_sec = 0;
        }
        if (out_nsec) {
            *out_nsec = 0;
        }
    }

    *out_len = (int)received;
    return 0;
}

void af_packet_close(int sockfd) {
    if (sockfd >= 0) {
        close(sockfd);
    }
}
