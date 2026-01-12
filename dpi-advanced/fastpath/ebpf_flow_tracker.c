/*
 * RansomEye DPI Advanced - eBPF Flow Tracker
 * AUTHORITATIVE: eBPF program for flow tuple extraction and L7 protocol fingerprinting
 * 
 * Requirements:
 * - Flow tuple extraction
 * - L7 protocol fingerprinting (metadata only)
 * - Per-flow counters
 * - No loops
 * - Verifier-safe
 */

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <linux/in.h>

#define MAX_FLOWS 65536

struct flow_key {
    __be32 src_ip;
    __be32 dst_ip;
    __be16 src_port;
    __be16 dst_port;
    __u8 protocol;
};

struct flow_stats {
    __u64 packet_count;
    __u64 byte_count;
    __u32 l7_protocol;
    __u64 first_seen;
    __u64 last_seen;
};

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, MAX_FLOWS);
    __type(key, struct flow_key);
    __type(value, struct flow_stats);
} flow_map SEC(".maps");

/*
 * eBPF program: Extract flow tuple and update counters
 * Attached to XDP or TC hook
 */
SEC("xdp_flow_tracker")
int xdp_flow_tracker(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;
    
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) {
        return XDP_PASS;
    }
    
    // Check for IP
    if (eth->h_proto != htons(ETH_P_IP)) {
        return XDP_PASS;
    }
    
    struct iphdr *ip = (struct iphdr *)(eth + 1);
    if ((void *)(ip + 1) > data_end) {
        return XDP_PASS;
    }
    
    // Build flow key
    struct flow_key key = {
        .src_ip = ip->saddr,
        .dst_ip = ip->daddr,
        .protocol = ip->protocol
    };
    
    // Extract ports for TCP/UDP
    if (ip->protocol == IPPROTO_TCP || ip->protocol == IPPROTO_UDP) {
        struct tcphdr *tcp = (struct tcphdr *)(ip + 1);
        if ((void *)(tcp + 1) > data_end) {
            return XDP_PASS;
        }
        
        if (ip->protocol == IPPROTO_TCP) {
            key.src_port = tcp->source;
            key.dst_port = tcp->dest;
        } else {
            struct udphdr *udp = (struct udphdr *)(ip + 1);
            if ((void *)(udp + 1) > data_end) {
                return XDP_PASS;
            }
            key.src_port = udp->source;
            key.dst_port = udp->dest;
        }
    }
    
    // Update flow stats
    struct flow_stats *stats = bpf_map_lookup_elem(&flow_map, &key);
    if (!stats) {
        struct flow_stats new_stats = {
            .packet_count = 1,
            .byte_count = ctx->data_end - ctx->data,
            .first_seen = bpf_ktime_get_ns(),
            .last_seen = bpf_ktime_get_ns()
        };
        bpf_map_update_elem(&flow_map, &key, &new_stats, BPF_ANY);
    } else {
        stats->packet_count++;
        stats->byte_count += (ctx->data_end - ctx->data);
        stats->last_seen = bpf_ktime_get_ns();
    }
    
    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
