#!/usr/bin/python

# This is a dummy peer that just illustrates the available information your peers 
# have available.  The setup script will copy it to create the versions you edit

import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer

class ramsStd(Peer):
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
        #logging.debug("%s again.  It's round %d." % (self.id, round))
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

            ########################################################################
            # The dummy client picks a single peer at random to unchoke.           #
            # You should decide a set of peers to unchoke accoring to the protocol #
            ########################################################################

            # number of requests is less than 4, so unchoke all peers
            if len(requests) < 4:
                for request in requests:
                    chosen.append(request)

            # number of requests is 4 or more, so unchoke the top 3 peers
            else: 
                # two lists, holding the download lists for the last three rounds
                recentDownloads1 = []
                recentDownloads2 = []

                # first round, so randomly unchoke
                if round == 0:
                    # grab one peer at random and add it to chosen if it's not a duplicate peer
                    for i in len(requests):
                        if len(chosen) == 3:
                            break

                        request = random.choice(requests)
                        if request not in chosen:
                            chosen.append(request)
                
                # second round, so decide first 3 unchokes just based off the last round
                elif round == 1:
                    # grab the list of downloads from the last round
                    recentDownloads1 = history.downloads[round-1]

                    # filter so that the only Download objects are the one where to_id == self.id
                    recentDownloads1 = list(filter(self.idChecker, recentDownloads1))

                    # sort based on blocks downloaded
                    recentDownloads1.sort(key=lambda x: x.blocks, reverse=True)

                    # add the requests to chosen that correspond to the from_id of the 3 Download objects that have the highest number of blocks downloaded
                    for download in recentDownloads1:
                        # max number of requests to unchoke reached
                        if len(chosen) == 3:
                            break

                        for i in range(len(requests)):
                            if requests[i].requester_id == download.from_id:
                                chosen.append(requests[i])

                # third round or later, so decide based off last 2 rounds
                else:
                    # grab the list of downloads from the last 2 rounds
                    recentDownloads1 = history.downloads[round-1]
                    recentDownloads2 = history.downloads[round-2]
                
                    # for each downloads list, filter so that the only Download objects are the one where to_id == self.id
                    recentDownloads1 = list(filter(self.idChecker, recentDownloads1))
                    recentDownloads2 = list(filter(self.idChecker, recentDownloads2))

                    # add all the Download objects to a new list, sort based on blocks downloaded
                    allRecentDownloads = recentDownloads1 + recentDownloads2
                    allRecentDownloads.sort(key=lambda x: x.blocks, reverse=True)

                    # add the requests to chosen that correspond to the from_id of the 3 Download objects that have the highest number of blocks downloaded
                    for download in allRecentDownloads:
                        # max number of requests to unchoke reached
                        if len(chosen) == 3:
                            break

                        for i in range(len(requests)):
                            if requests[i].requester_id == download.from_id:
                                chosen.append(requests[i])
                    
                    # 3 rounds have passed, so get an optimistic unchoke
                    if round+1 % 3 == 0:
                        # grab one peer at random and add it to chosen if it's not a duplicate peer
                        for i in len(requests):
                            request = random.choice(requests)
                            if request not in chosen:
                                chosen.append(request)
                                break

            
        # Now that we have chosen who to unchoke, the standard client evenly shares its bandwidth among them
        if len(chosen) == 0:
            bws = []
        else:
            bws = even_split(self.up_bw, len(chosen))

        # create actual uploads out of the list of peer ids and bandwidths
        # You don't need to change this
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]

        return uploads
