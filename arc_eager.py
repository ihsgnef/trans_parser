from collections import defaultdict

WORD  = 0
POS   = 1
HEAD  = 2
LABEL = 3
ROOT  = -1

class Configuration:

    def __init__(self, root, buffer, sentence):
        self.arcs = []
        self.stack = [root]
        self.buffer = buffer
        self.sentence = sentence

    def __str__(self):
        ret = 'stack: ' + list(self.stack).__str__() + '\n'
        ret += 'buffer: ' + list(self.buffer).__str__() + '\n'
        ret += 'arcs: ' + self.arcs.__str__()
        return ret


class GoldConfiguration:

    def __init__(self):
        self.head_of = {}
        self.deps_of = defaultdict(lambda : [])
        self.arcs = set()


class ArcEager:
    
    LEFT   = 0
    RIGHT  = 1
    SHIFT  = 2
    REDUCE = 3
    TRANSITIONS = [LEFT, RIGHT, SHIFT, REDUCE]
    TRANSITION_NAMES = ['LEFT', 'RIGHT', 'SHIFT', 'REDUCE']
    transition_funcs = {}

    def __init__(self):
        ArcEager.transition_funcs[ArcEager.LEFT] = ArcEager.left_arc
        ArcEager.transition_funcs[ArcEager.RIGHT] = ArcEager.right_arc
        ArcEager.transition_funcs[ArcEager.SHIFT] = ArcEager.shift
        ArcEager.transition_funcs[ArcEager.REDUCE] = ArcEager.reduce

    @staticmethod
    def get_initial_config(sentence):
        '''
        construct initial configuration from given sentence
        buffer is constructed with an extra root
        root is -1
        '''
        buffer = list(range(len(sentence)))
        return Configuration(ROOT, buffer, sentence)

    @staticmethod
    def get_gold_config(sentence):
        gold_config = GoldConfiguration()
        for i in xrange(len(sentence)):
            head = sentence[i][HEAD]
            gold_config.head_of[i] = head
            gold_config.deps_of[head].append(i)
            gold_config.arcs.add((head, i))
        return gold_config

    @staticmethod
    def is_finished(config):
        '''
        finish when buffer is empty 
        and only root is left in stack
        '''
        return len(config.buffer) == 0 and len(config.stack) == 1

    @staticmethod
    def is_not_projective(config):
        for d1 in config.head_of.keys():
            h1 = config.head_of[d1]
            for d2 in config.head_of.keys():
                h2 = config.head_of[d2]
                if h1 is ROOT or h2 is ROOT:
                    continue
                # h1 h2 d1 d2
                if h1 < h2 and h2 < d1 and d1 < d2:
                    return True
                # d1 h2 h1 d2
                if d1 < h2 and h2 < h1 and h1 < d2:
                    return True
                # h1 d2 d1 h2
                if h1 < d2 and d2 < d1 and d1 < h2:
                    return True
                # d1 d2 h1 h2
                if d1 < d2 and d2 < h1 and h1 < h2:
                    return True
        return False

    @staticmethod
    def get_legal_transitions(config):
        '''
        get the legal transitions in given configuration
        '''
        is_legal = [True for _ in ArcEager.TRANSITIONS]

        if len(config.buffer) == 0:
            # buffer is empty, cannot do arc or shift
            is_legal[ArcEager.LEFT] = False
            is_legal[ArcEager.RIGHT] = False
            is_legal[ArcEager.SHIFT] = False
        else:
            # precondition for right_arc: buffer_first is not root 
            # and does not already have a head
            buffer_first = config.buffer[0]

            if buffer_first is ROOT:
                is_legal[ArcEager.RIGHT] = False

            if len([h for h, t in config.arcs if t == buffer_first]) > 0:
                is_legal[ArcEager.RIGHT] = False

        if len(config.stack) == 0:
            # stack is empty, cannot do left_arc or right_arc
            is_legal[ArcEager.LEFT] = False
            is_legal[ArcEager.RIGHT] = False
            is_legal[ArcEager.REDUCE] = False
        else:
            # precondition for left_arc: stack_top is not root 
            # and does not already have a head
            stack_top = config.stack[-1]

            if stack_top is ROOT:
                is_legal[ArcEager.LEFT] = False

            if len([h for h, t in config.arcs if t == stack_top]) > 0:
                is_legal[ArcEager.LEFT] = False
            else:
                is_legal[ArcEager.REDUCE] = False

        legal_transitions = [trans for trans, legal in enumerate(is_legal)
                             if legal is True]
        return legal_transitions

    @staticmethod
    def left_arc(config):
        '''
        pop stack
        add (buffer_first, stack_top)
        '''
        s = config.stack.pop()
        b = config.buffer[0]
        config.arcs.append((b, s))
        return config
    
    @staticmethod
    def right_arc(config):
        '''
        move buffer_first to stack
        add (stack_top, buffer_first)
        '''
        s = config.stack[-1]
        b = config.buffer[0]
        del config.buffer[0]
        config.stack.append(b)
        config.arcs.append((s, b))
        return config

    @staticmethod
    def shift(config):
        ''' move buffer_first to stack '''
        b = config.buffer[0]
        del config.buffer[0]
        config.stack.append(b)
        return config

    @staticmethod
    def reduce(config):
        ''' pop stack '''
        config.stack.pop()
        return config

    @staticmethod
    def take_transition(config, transition):
        '''
        take the given transition on the given config
        return the new config
        '''
        assert transition in ArcEager.TRANSITIONS
        return ArcEager.transition_funcs[transition](config)

    @staticmethod
    def static_oracle(config, gold_config):
        if len(config.buffer) == 0:
            if len(config.stack) == 0:
                return None
            else:
                return [ArcEager.REDUCE]
        b = config.buffer[0]
        if len(config.stack) == 0:
            return [ArcEager.SHIFT]
        s = config.stack[-1]
        if s is not ROOT and b == gold_config.head_of[s]:
            return [ArcEager.LEFT]
        if s == gold_config.head_of[b]:
            return [ArcEager.RIGHT]
        if gold_config.head_of[b] < s:
            return [ArcEager.REDUCE]
        if b in gold_config.deps_of:
            if len([x for x in gold_config.deps_of[b] if x < s]):
                return [ArcEager.REDUCE]
        return [ArcEager.SHIFT]

    @staticmethod
    def dynamic_oracle(config, gold_config):
        transitions = []
        legal = ArcEager.get_legal_transitions(config)
        is_ok = dict((t, t in legal) for t in ArcEager.TRANSITIONS)
        
        if is_ok[ArcEager.LEFT]:
            if ArcEager.left_arc_cost(config, gold_config):
                is_ok[ArcEager.LEFT] = False
        if is_ok[ArcEager.RIGHT]:
            if ArcEager.right_arc_cost(config, gold_config):
                is_ok[ArcEager.RIGHT] = False
        if is_ok[ArcEager.SHIFT]:
            if ArcEager.shift_cost(config, gold_config):
                is_ok[ArcEager.SHIFT] = False
        if is_ok[ArcEager.REDUCE]:
            if ArcEager.reduce_cost(config, gold_config):
                is_ok[ArcEager.REDUCE] = False

        ok_transitions = [t for t, ok in is_ok.items() if ok]
        return ok_transitions
    
    @staticmethod
    def left_arc_cost(config, gold_config):
        '''
        cost: number of arcs (k, s) and (s, k) in gold_config with k in buffer
        '''
        assert len(config.stack) > 0 and len(config.buffer) > 0
        b = config.buffer[0]
        s = config.stack[-1]
        assert s is not ROOT
        if (b, s) in gold_config.arcs:
            return 0
        ks = [gold_config.head_of[s]]
        ks += gold_config.deps_of[s]
        cost = len(set(ks).intersection(set(config.buffer)))
        return cost

    @staticmethod
    def right_arc_cost(config, gold_config):
        '''
        cost: number of arcs (k, b) in gold_config with k in stack or buffer
        and number of arcs (b, k) in gold_config with k in stack
        '''
        assert len(config.stack) > 0 and len(config.buffer) > 0
        b = config.buffer[0]
        s = config.stack[-1]
        assert b is not ROOT
        if (s, b) in gold_config.arcs:
            return 0
        cost = 0
        cost += gold_config.head_of[b] in config.stack
        cost += gold_config.head_of[b] in config.buffer
        ks = set(gold_config.deps_of[b])
        cost += len(ks.intersection(set(config.stack)))
        return cost

    @staticmethod
    def shift_cost(config, gold_config):
        '''
        cost: number of arcs (k, b) and (b, k) in gold_config with k in stack
        '''
        assert len(config.buffer) > 0
        b = config.buffer[0]
        cost = 0
        for k in config.stack:
            cost += k == gold_config.head_of[b]
            cost += k in gold_config.deps_of[b]
        cost = max(0, cost)
        return cost

    @staticmethod
    def reduce_cost(config, gold_config):
        '''
        cost: number of arcs (s, k) in gold_config with k in buffer
        '''
        assert len(config.stack) > 0
        s = config.stack[-1]
        deps = set(gold_config.deps_of[s])
        cost = len(deps.intersection(set(config.buffer)))
        return cost


if __name__ == '__main__':
    # sentence = "economic news had little effect on financial markets .".split()
    # arcsys = ArcEager()
    # transitions = [2, 0, 2, 0, 1, 2, 0, 1, 1, 2, 0, 1, 3, 3, 3, 1]
    # config = arcsys.get_initial_config(sentence)
    # print config
    # 
    # for t in transitions:
    #     print arcsys.TRANSITION_NAMES[t]
    #     if t in arcsys.get_legal_transitions(config):
    #         config = arcsys.take_transition(t, config)
    #         print config
    #     else:
    #         print 'not legal'
    #     if arcsys.is_finished(config):
    #         print 'finished'
    #         break

    import util
    f = 'en.tr100'
    ss = util.read_conll_data(f)
    sentence = ss[30]
    arcsys = ArcEager()
    config = arcsys.get_initial_config(sentence)
    print config
    gold_config = arcsys.get_gold_config(sentence)
    gold_arcs = gold_config.arcs
    print gold_arcs
    print

    if not arcsys.is_not_projective(gold_config):
        while not arcsys.is_finished(config):
            action = arcsys.static_oracle(config, gold_config)
            print arcsys.TRANSITION_NAMES[action]
            config = arcsys.take_transition(config, action)
            print config
            print gold_arcs - set(config.arcs)
            print
    else:
        print 'not projective'
