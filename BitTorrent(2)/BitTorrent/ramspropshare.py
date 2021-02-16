#!/usr/bin/python

# This is a dummy peer that just illustrates the available information your peers 
# have available.  The setup script will copy it to create the versions you edit

import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer

class ramsPropShare(Peer):
    def post_init(self):
        print("post_init(): %s here!" % self.id)
        ##################################################################################
        # Declare any variables here that you want to be able to access in future rounds #
        ##################################################################################

        #This commented out code is and example of a python dictionsary,
        #which is a convenient way to store a value indexed by a particular "key"
        #self.dummy_state = dict()
        #self.dummy_state["cake"] = "lie"
    
    def requests(self, peers, history):
        """
        peers: available info about the peers (who has what pieces)
        history: what's happened so far as far as this peer can see

        returns: a list of Request() objects

        This will be called after update_pieces() with the most recent state.
        """
        #Calculate the pieces you still need
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = list(filter(needed, list(range(len(self.pieces)))))
        np_set = set(needed_pieces)  # sets support fast intersection ops.


        """logging.debug("%s here: still need pieces %s" % (self.id, needed_pieces))

        #This code shows you what you have access to in peers and history
        #You won't need it in your final solution, but may want to uncomment it
        #and see what it does to help you get started
        
        logging.debug("%s still here. Here are some peers:" % self.id)
        for p in peers:
            logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))

        logging.debug("And look, I have my entire history available too:")
        logging.debug("look at the AgentHistory class in history.py for details")
        logging.debug(str(history))"""
        
        

        requests = []   # We'll put all the things we want here
        # Symmetry breaking is good...
        random.shuffle(needed_pieces)

        # count frequencies of all pieces that the other peers have
        # this will be useful for implementing rarest first
        ###########################################################
        # you'll need to write the code to compute these yourself #
        ###########################################################
        frequencies = {}
        
        for p in peers:
            for piece in p.available_pieces:
                if piece in frequencies:
                    frequencies[piece] += 1
                else:
                    frequencies[piece] = 1

        
        # Python syntax to perform a sort using a user defined sort key
        # This exact sort is probably not a useful sort, but other sorts might be useful
        # peers.sort(key=lambda p: p.id)

        # request all available pieces from all peers!
        # (up to self.max_requests from each)
        #############################################################################
        # This code asks for pieces at random, you need to adapt it to rarest first #
        #############################################################################
        for peer in peers:
            av_set = set(peer.available_pieces)
            isect = av_set.intersection(np_set)
            n = min(self.max_requests, len(isect))
            dict1 = {}
            minList = []
            for i in isect:
                dict1[i] = frequencies[i]
            for i in range(int(n)):
                temp = min(dict1, key=dict1.get)
                minList.append(temp)
                del dict1[temp]

            for id in minList:
                starting_block = self.pieces[id]
                r = Request(self.id, peer.id, id, starting_block)
                requests.append(r)
            
        return requests

    def idChecker(self, currentDownload):
        if (self.id == currentDownload.to_id):
            return True

        return False

    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round
        peers -- available info about all the peers
        history -- history for all previous rounds

        returns: list of Upload objects.

        In each round, this will be called after requests()
        """

        ##############################################################################
        # The code and suggestions here will get you started for the standard client #
        # You'll need to change things for the other clients                         #
        ##############################################################################

        round = history.current_round()
        logging.debug("%s again.  It's round %d." % (
            self.id, round))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to the client in
        # the previous round

        chosen = [] # list to hold all of the peers to be unchoked
        bws = [] # list to hold the allocated bandwidth of the client for each unchoked peer

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
        else:
            logging.debug("Still here: uploading to a random peer")

            # first round, so just split bandwidth evenly among all peers
            if round == 0:
                bws = even_split(self.up_bw, len(requests))
                
                chosen = requests

            # second round or later, so the propshare client proportionally shares its bandwidth across its peers
            else:
                # get a set of the peers that the client received blocks from last round 
                downloadedPeers = set()
                for download in history.downloads[round-1]:
                    if download.to_id == self.id:
                        downloadedPeers.add(download.from_id) 

                # get a list of the peers that are requesting blocks from the client this round
                requestingPeers = set()
                for request in requests:
                    requestingPeers.add(request.peer_id)

                # Compare both sets and create two lists (and a dictionary): #
                    # list that holds peers that the client received blocks from last round and are requesting blocks from the client this round
                    # dictionary that holds the total amount of blocks downloaded from each preferred peer
                    preferredPeers = []
                    downloadedBlocks = dict()
                    for peer in downloadedPeers:
                        if peer in requestingPeers:
                            preferredPeers.append(peer)
                            downloadedBlocks[peer] = 0

                    # list that holds peers that the client did NOT receive blocks from last round and are requesting blocks from the client this round
                    optimisticPeers = []
                    for peer in requestingPeers:
                        if peer not in downloadedPeers:
                            optimisticPeers.append(peer)
                    
                    # add the requests of the preferred peers to chosen
                    for request in requests:
                        if request.requester_id in preferredPeers:
                            chosen.append(request)
                    
                    # grab one optimistic peer at random and add it to chosen 
                    for request in requests:
                        optimisticUnchoke = random.choice(optimisticPeers)
                        if optimisticUnchoke == request.requester_id:
                            chosen.append(optimisticUnchoke)
                            break

                # get the total number of blocks downloaded across all preferred peers, and the total number of blocks downloaded from each specific preferred peer
                totalBlocksFromPreferred = 0
                for download in history.downloads[round-1]:
                    if download.from_id in preferredPeers:
                        totalBlocksFromPreferred+= download.blocks
                        downloadedBlocks[download.from_id]+= download.blocks

                # allocate the client's bandwidth for each preferred peer, proportional to the amount of blocks the client downloaded from the peer
                for peer in preferredPeers:
                    proportionOfbandwidth = (downloadedBlocks[peer] / totalBlocksFromPreferred * .90)
                    bws.append(proportionOfbandwidth)

                # allocate a constant 10% of the client's bandwidth for the optimistic unchoke
                bws.append(.10 * self.up_bw)


        # create actual uploads out of the list of peer ids and bandwidths
        # You don't need to change this
        uploads = [Upload(self.id, peer_id, bw)
                for (peer_id, bw) in zip(chosen, bws)]
            
        return uploads
