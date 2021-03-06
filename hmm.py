#!/usr/bin/env python
#
# Copyright (c) 2014 Michael Strosaker

import itertools, math

class state:
    def __init__(self, name, p_initial, p_emission, p_transition,
                 p_termination=0.0):
        self.name = name			# string
        self.p_initial = p_initial		# float (between 0.0 and 1.0)
        self.p_emission = p_emission		# dictionary (string: float)
        self.p_transition = p_transition	# dictionary (string: float)
        self.p_termination = p_termination	# float (between 0.0 and 1.0)

    def __repr__(self):
        ret = ['hmm.state(']
        ret.append("'%s'," % self.name)
        ret.append('%f,' % self.p_initial)
        ret.append('%s,' % repr(self.p_emission))
        ret.append('%s,' % repr(self.p_transition))
        ret.append('%f' % self.p_termination)
        ret.append(')')
        return '\n'.join(ret)

class hmm:
    def __init__(self, alphabet, states):
        """
        Creates a new hidden Markov model object.

        Parameters:
          - alphabet: a list of strings, where each string represents a
            symbol that can possibly be emitted by any of the states in
            the model (for example, ['A', 'C', 'G', 'T'] for genomic data)
          - states: a list of state objects

        The initial distribution vector (usually referred to as pi) is
        described by the states with non-zero values for p_initial.

        If at least one of the states in the states parameter includes a
        non-zero p_termination, then there is an implied "end" state.
        In that case, only those states with a non-zero p_termination
        can be the last state in a valid sequence of states.

        TODO: Data validation:
          - ensure that all of the p_initial probabilities add up to
            (about) 1,0
          - ensure that the probabilities in the p_emission dictionaries
            add up to (about) 1.0 for each state
          - ensure that the probabilities in the p_transition dictionaries
            (plus p_termination, if non-zero) add up to (about) 1.0 for
            each state
          - ensure that there are no duplicate state names
          - ensure that no states will attempt to transition to non-
            existent states
          - ensure that no states will emit values that are not in the
            specified alphabet
          - ensure that all states are reachable
        """
        self.alphabet = alphabet
        self.terminal_state = False
        self.initial_states = []
        self.terminating_states = []
        self.states = {}
        for state in states:
            self.states[state.name] = state
            if state.p_initial > 0.0:
                self.initial_states.append(state.name)
            if state.p_termination > 0.0:
                self.terminal_state = True
                self.terminating_states.append(state.name)

    def __repr__(self):
        ret = ['hmm.hmm(']
        ret.append('%s,' % self.alphabet)
        ret.append('[')
        for s_name, s in self.states.iteritems():
            ret.append('%s,' % repr(s))
        ret.append(']')
        ret.append(')')
        return '\n'.join(ret)

    def score(self, seq_state, seq_observed):
        """
        Calculates the log (base 10) of the probability of observing this
        sequence of states and observations.

        Parameters:
          - seq_state: a list of strings, representing an ordered sequence
            of states in the HMM
          - seq_observed: a list of strings, representing an ordered sequence
            of symbols that were observed
        Returns:
          - a float, representing the log (base 10) of the probability
            of the state sequence being observed
          - None if the specified state sequence is invalid because:
           - the first state in the sequence cannot be an initial state (has
             a p_initial of 0)
           - there is no edge between two consecutive states in the state
             sequence (i.e., the probability of transitioning from state[i] to
             state[i+1] is 0 for some i)
           - a state cannot emit the corresponding symbol in the sequence of
             observations (i.e., seq_state[i] cannot emit seq_observed[i] for
             some i)
           - the model has a terminating state, and the last state in the
             sequence does not have an edge to the terminating state

        TODO: Data validation:
          - ensure that the specified sequence of observations only
            includes symbols present in the alphabet
        """

        # if there is an implied terminal state, make sure the last state
        # in the specified sequence has an edge to it
        if self.terminal_state:
            if seq_state[-1] not in self.terminating_states:
                return None

        p = 0.0
        state_prev = None
        for i in range(len(seq_state)):
            state_cur = self.states[seq_state[i]]
            if i == 0:
                # if the initial probability for this state is 0, then
                # this is not a valid sequence of states
                if state_cur.p_initial == 0.0:
                    return None

                p += math.log10(state_cur.p_initial)

            else:
                # check that the prior state can transition to this one
                if seq_state[i] not in state_prev.p_transition.keys():
                    return None

                p += math.log10(state_prev.p_transition[seq_state[i]])

            # check that this state can emit the observed alphabet symbol
            if seq_observed[i] not in state_cur.p_emission.keys():
                return None

            if state_cur.p_emission[seq_observed[i]] == 0.0:
                return None

            p += math.log10(state_cur.p_emission[seq_observed[i]])

            state_prev = state_cur

        return p

    def enumerate(self, observed):
        """
        Enumerates and prints every possible path of states that can
        explain an observed sequence of symbols, along with the probability
        associated with each of the state sequences.

        *** IMPORTANT NOTE: ***
        Enumerating all possible state sequences is an expensive operation
        for models with many states and for long observations.  The number
        of state sequences in the overall enumeration is:
            (#states)^(len(observation))

        Parameters:
          - seq_observed: a list of strings, representing an ordered sequence
            of symbols that were observed
        Returns: (nothing)

        TODO: Data validation:
          - ensure that the specified sequence of observations only
            includes symbols present in the alphabet
        """
        best_seq = None
        best_score = None
        for seq in itertools.product(self.states.keys(), repeat=len(observed)):
            s = self.score(seq, observed)
            if s is not None:
                print '%s: %f' % (seq, s)
                if best_score is None:
                    best_seq = seq
                    best_score = s
                elif s > best_score:
                    best_seq = seq
                    best_score = s

        print 'BEST: %s: %f' % (best_seq, best_score)

    def _p_emit(self, state, observation):
        """
        Retrieves the probability of a state emitting a given symbol.
        """
        if state not in self.states.keys():
            return None
        if observation not in self.states[state].p_emission.keys():
            return 0.0
        return self.states[state].p_emission[observation]

    def _p_transition(self, from_state, to_state):
        """
        Retrieves the probability of a state transitioning to a given state.
        """
        if from_state not in self.states.keys():
            return None
        if to_state not in self.states[from_state].p_transition.keys():
            return 0.0
        return self.states[from_state].p_transition[to_state]

    def _connected(self, from_state, to_state):
        """
        Establishes whether there is an edge between two given states.

        Parameters:
          - from_state: a state in the states member of this object
          - to_state: a state in the states member of this object
        Returns:
          - True if there is an edge from from_state to to_state
          - False if there is no such edge, or if the from_state does not
            exist
        """
        if from_state not in self.states.keys():
            return False
        if to_state not in self.states[from_state].p_transition.keys():
            return False
        if self.states[from_state].p_transition[to_state] > 0.0:
            return True
        return False

    def trellis(self, observed):
        """
        Builds a trellis of the probabilities of the possible paths,
        given a sequence of observed symbols.

        Parameters:
          - observed: a sequence of observed symbols
        Returns:
          - a list of dictionaries, one dictionary per symbol in the
            observations; each dictionary represents a column of the trellis

        TODO: Data validation:
          - ensure that the specified sequence of observations only
            includes symbols present in the alphabet
        """
        state_names = self.states.keys()
        trellis = []
        prior_probs = None

        for i in range(len(observed)):
            probs = {}

            if i == 0:
                # first state; only those states with initial probabilities
                # can have non-None values in this column
                for state in state_names:
                    p_init = self.states[state].p_initial
                    p_emit = self._p_emit(state, observed[i])
                    if p_init == 0.0 or p_emit == 0.0:
                        probs[state] = None
                    else:
                        probs[state] = math.log10(p_init) + \
                                       math.log10(p_emit)

            else:
                for state in state_names:
                    p_emit = self._p_emit(state, observed[i])
                    if p_emit == 0.0:
                        probs[state] = None
                    else:
                        best = None
                        for prev_state, prev_prob in prior_probs.iteritems():
                            if prev_prob is None:
                                continue
                            if self._connected(prev_state, state):
                                p_tran = self._p_transition(prev_state, state)
                                s = prev_prob + math.log10(p_emit) + \
                                      math.log10(p_tran)
                                if best == None:
                                    best = s
                                elif s > best:
                                    best = s
                        probs[state] = best

            # the last column of the trellis can only include those states
            # that can transition to the implied terminal state, if one exists
            if i == (len(observed)-1):
                if self.terminal_state:
                    for s in state_names:
                        if s not in self.terminating_states:
                            probs[s] = None
                        else:
                            probs[s] += math.log10(self.states[s].p_termination)

            trellis.append(probs)
            prior_probs = probs

        return trellis

    def viterbi_path(self, observed):
        """
        Establish the most probable path of states that explains a sequence
        of observations, along with the probability of that path being
        observed.

        Parameters:
          - seq_observed: a list of strings, representing an ordered sequence
            of symbols that were observed
        Returns:
          - a tuple of two values:
            - a list of state names that explains the observations
            - a float, representing the log (base 10) of the probability
              of the sequence being observed
        """
        trellis = self.trellis(observed)

        # start with the best (largest) value in the last column of the
        # trellis; we will work backwards from here
        probs = trellis[-1]
        next_state = max(probs, key=probs.get)
        state_seq = [next_state]
        p_overall = probs[next_state]

        for i in reversed(range(len(trellis)-1)):
            probs = trellis[i]
            states = probs.keys()
            # eliminate the states that cannot transition to the (known)
            # next state
            for state in states:
                if probs[state] == None:
                    del probs[state]
                elif not self._connected(state, next_state):
                    del probs[state]
            next_state = max(probs, key=probs.get)
            state_seq.append(next_state)

        state_seq.reverse()   # because the list of states was built backwards
        return (state_seq, p_overall)

def train_hmm(training_data, include_terminal_state=False):
    """
    Create a new HMM based solely on annotated training data.  Both the
    topology of the state interconnections and the probabilities of the
    emissions and transitions are inferred from training data.

    Parameters:
      - training_data: a list of tuples; each tuple consists of two lists
        of the same length:
        - a list of symbols
        - a list of states corresponding to the sequence that best explains
          the list of symbols
      - include_terminal_state: a boolean, indicating whether an implied
        terminal state should be included in the model
    Returns:
      - a new hmm object, ready for use

    TODO: data validation; ensure that the lengths of the two lists in
    each tuple is exactly the same length
    """
    # determine the list of states and alphabet of symbols
    alphabet = []
    state_names = []
    for sample in training_data:
        alphabet.extend(list(set(sample[0])))
        state_names.extend(list(set(sample[1])))
    alphabet = list(set(alphabet))
    state_names = list(set(state_names))

    states = []
    for s_name in state_names:
        states.append(state(s_name, 0.0, None, None))

    # calculate the initial probabilities
    s_dict = {}
    for s in state_names:
        s_dict[s] = 0
    for sample in training_data:
        s_dict[sample[1][0]] += 1
    for s in states:
        s.p_initial = s_dict[s.name] / (len(training_data) * 1.0)

    # calculate the emission probabilities for each state
    for s in states:
        emit = {}
        total = 0
        for sample in training_data:
            for i in range(len(sample[1])):
                if sample[1][i] == s.name:
                    total += 1
                    emit[sample[0][i]] = emit.get(sample[0][i], 0) + 1
        for e in emit.keys():
            emit[e] = emit[e] / (total * 1.0)
        s.p_emission = emit

    # calculate the transition probabilities for each state
    for s in states:
        tran = {}
        total = 0
        term = 0
        for sample in training_data:
            for i in range(len(sample[1])-1):
                if sample[1][i] == s.name:
                    total += 1
                    tran[sample[1][i+1]] = tran.get(sample[1][i+1], 0) + 1
            if include_terminal_state:
                if sample[1][-1] == s.name:
                    total += 1
                    term += 1
        for t in tran.keys():
            tran[t] = tran[t] / (total * 1.0)
        s.p_transition = tran
        if include_terminal_state:
            s.p_termination = term / (total * 1.0)

    return hmm(alphabet, states)

