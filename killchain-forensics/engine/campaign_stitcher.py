#!/usr/bin/env python3
"""
RansomEye KillChain & Forensics - Campaign Stitcher
AUTHORITATIVE: Deterministic correlation of incidents across hosts, users, IPs, malware families
"""

from typing import List, Dict, Any, Set, Optional
import uuid


class CampaignStitchingError(Exception):
    """Base exception for campaign stitching errors."""
    pass


class CampaignStitcher:
    """
    Deterministic campaign correlation.
    
    Links incidents across:
    - Hosts
    - Users
    - IPs
    - Malware families
    
    All linking rules are deterministic (no randomness).
    """
    
    def __init__(self):
        """Initialize campaign stitcher."""
        self.campaigns: Dict[str, Dict[str, Any]] = {}
        self.host_to_campaign: Dict[str, str] = {}
        self.user_to_campaign: Dict[str, str] = {}
        self.ip_to_campaign: Dict[str, str] = {}
        self.malware_to_campaign: Dict[str, str] = {}
    
    def create_campaign(self) -> str:
        """
        Create new campaign.
        
        Returns:
            Campaign identifier (UUID)
        """
        campaign_id = str(uuid.uuid4())
        self.campaigns[campaign_id] = {
            'campaign_id': campaign_id,
            'hosts': set(),
            'users': set(),
            'ip_addresses': set(),
            'malware_families': set(),
            'events': []
        }
        return campaign_id
    
    def link_event(
        self,
        event: Dict[str, Any],
        correlation_metadata: Dict[str, Any]
    ) -> str:
        """
        Link event to campaign using deterministic rules.
        
        Linking rules (in order):
        1. If event shares IP with existing campaign, link to that campaign
        2. If event shares malware family with existing campaign, link to that campaign
        3. If event shares user with existing campaign, link to that campaign
        4. If event shares host with existing campaign, link to that campaign
        5. Otherwise, create new campaign
        
        Args:
            event: Killchain event dictionary
            correlation_metadata: Correlation metadata (IPs, malware families, etc.)
        
        Returns:
            Campaign identifier
        """
        host_id = event.get('host_id', '')
        user_id = event.get('user_id', '')
        ip_addresses = correlation_metadata.get('ip_addresses', [])
        malware_families = correlation_metadata.get('malware_families', [])
        
        # Try to find existing campaign (deterministic rules)
        campaign_id = None
        
        # Rule 1: Link by IP
        for ip in ip_addresses:
            if ip in self.ip_to_campaign:
                campaign_id = self.ip_to_campaign[ip]
                break
        
        # Rule 2: Link by malware family
        if not campaign_id:
            for malware in malware_families:
                if malware in self.malware_to_campaign:
                    campaign_id = self.malware_to_campaign[malware]
                    break
        
        # Rule 3: Link by user
        if not campaign_id and user_id:
            if user_id in self.user_to_campaign:
                campaign_id = self.user_to_campaign[user_id]
        
        # Rule 4: Link by host
        if not campaign_id and host_id:
            if host_id in self.host_to_campaign:
                campaign_id = self.host_to_campaign[host_id]
        
        # Rule 5: Create new campaign
        if not campaign_id:
            campaign_id = self.create_campaign()
        
        # Update campaign with event data
        campaign = self.campaigns[campaign_id]
        if host_id:
            campaign['hosts'].add(host_id)
            self.host_to_campaign[host_id] = campaign_id
        if user_id:
            campaign['users'].add(user_id)
            self.user_to_campaign[user_id] = campaign_id
        for ip in ip_addresses:
            campaign['ip_addresses'].add(ip)
            self.ip_to_campaign[ip] = campaign_id
        for malware in malware_families:
            campaign['malware_families'].add(malware)
            self.malware_to_campaign[malware] = campaign_id
        
        campaign['events'].append(event.get('event_id', ''))
        
        return campaign_id
    
    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """
        Get campaign by ID.
        
        Args:
            campaign_id: Campaign identifier
        
        Returns:
            Campaign dictionary, or None if not found
        """
        campaign = self.campaigns.get(campaign_id)
        if campaign:
            # Convert sets to lists for JSON serialization
            return {
                'campaign_id': campaign['campaign_id'],
                'hosts': list(campaign['hosts']),
                'users': list(campaign['users']),
                'ip_addresses': list(campaign['ip_addresses']),
                'malware_families': list(campaign['malware_families']),
                'events': campaign['events']
            }
        return None
    
    def get_all_campaigns(self) -> List[Dict[str, Any]]:
        """
        Get all campaigns.
        
        Returns:
            List of campaign dictionaries
        """
        return [self.get_campaign(cid) for cid in self.campaigns.keys()]
