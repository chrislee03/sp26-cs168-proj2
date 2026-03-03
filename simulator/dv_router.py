"""
Your awesome Distance Vector router for CS 168

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

import sim.api as api
from cs168.dv import (
    RoutePacket,
    Table,
    TableEntry,
    DVRouterBase,
    Ports,
    FOREVER,
    INFINITY,
)


class DVRouter(DVRouterBase):

    # A route should time out after this interval
    ROUTE_TTL = 15

    # -----------------------------------------------
    # At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # Determines if you send poison for expired routes
    POISON_EXPIRED = False

    # Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = False

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (
            self.SPLIT_HORIZON and self.POISON_REVERSE
        ), "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        self.ports = Ports()

        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self

        ##### Begin Stage 10A #####
        self.history = dict()
        ##### End Stage 10A #####

    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."

        ##### Begin Stage 1 #####
        curr_latency = self.ports.get_latency(port)
        self.table[host] = TableEntry(dst=host, port=port, latency=curr_latency, expire_time=FOREVER)

        for host, entry in self.table.items():
            print("Route to {} has a latency of {}".format(host, entry.latency))


        ##### End Stage 1 #####

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        
        ##### Begin Stage 2 #####

        #Find the route first
        entry = self.table.get(packet.dst)
       
       # Drop Packet if no route exists
        if entry is None: 
            return
        
        #Drop Packet is route latency is greater than or equal to INFINITY
        if entry.latency >= INFINITY:
            return
        
        # Drop Packet if outgoing link latency is greater then or equal to INFINITY
        link_latency = self.ports.get_latency(entry.port)
        if link_latency >= INFINITY:
            return

        self.send(packet, port= entry.port)


        ##### End Stage 2 #####

    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        """
        
        ##### Begin Stages 3, 6, 7, 8, 10 #####
        for host, entry in self.table.items():
            if entry:
                ports = single_port if single_port else self.ports.get_all_ports() 
                for port in ports:
                    if self.SPLIT_HORIZON and entry.port == port:
                        continue
                    latency = INFINITY if (self.POISON_REVERSE and entry.port == port) else min(entry.latency, INFINITY)
                    if not force and port in self.history and host in self.history[port] and self.history[port][host] == latency:
                         continue
                    
                    if port not in self.history:
                        self.history[port] = {}
                    self.history[port][host] = latency
                    self.send_route(port, host, latency)
        ##### End Stages 3, 6, 7, 8, 10 #####

    def expire_routes(self):
        """
        Clears out expired routes from table.
        accordingly.
        """
        
        ##### Begin Stages 5, 9 #####
        for host, entry in list(self.table.items()):
            if entry.expire_time != FOREVER and entry.expire_time <= api.current_time():
                self.handle_poison(host, entry)
        ##### End Stages 5, 9 #####

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        """
        
        ##### Begin Stages 4, 10 #####
        curr_route = self.table.get(route_dst)
        new_latency = route_latency + self.ports.get_latency(port)
        if not curr_route or curr_route.port == port or new_latency < curr_route.latency:
            self.table[route_dst] = TableEntry(dst=route_dst, port=port, latency=new_latency, expire_time=(api.current_time() + self.ROUTE_TTL))
            self.send_routes(force=False)
        ##### End Stages 4, 10 #####

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.ports.add_port(port, latency)

        ##### Begin Stage 10B #####
        if self.SEND_ON_LINK_UP:
            self.send_routes(single_port = port)
        ##### End Stage 10B #####

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router goes down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        self.ports.remove_port(port)

        ##### Begin Stage 10B #####
        for host, entry in list(self.table.items()):
            if entry.port == port:
                self.handle_poison(host, entry)
        self.send_routes(force=False)
        ##### End Stage 10B #####

    # Feel free to add any helper methods!
    def handle_poison(self, host, entry):
        if self.POISON_EXPIRED or self.POISON_ON_LINK_DOWN:
            self.table[host] = TableEntry(dst=host, port=entry.port, latency=INFINITY, expire_time=(api.current_time()+self.ROUTE_TTL))
        else: 
            self.table.pop(host)
