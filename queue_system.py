import numpy as np
from abc import abstractmethod
import networkx as nx
from tqdm import tqdm
from matplotlib import pyplot as plt

from data_parcser import Server, ServiceTable, Customer
from eval import F_s

INF = 1000000

class QueueSystem:
    '''
        仿真参数：
         - simulation_time: 仿真时长, int
         - queue_capacity: 队伍容量, int
         - call_center_structure: 呼叫中心结构, networkx.Graph
         - router: 路由规则, string
         - AWT: Acceptable waiting time, float
         - SL_threshold: service level threshold, float
    '''

    def __init__(self, simulation_time, queue_capacity, call_center_structure, router, AWT, SL_threshold):
        self.T = simulation_time
        self.t = 0
        self.queue_capacity = queue_capacity
        self.structure = call_center_structure
        self.router = router
        self.AWT = AWT
        self.SL_threshold = SL_threshold
        self.K = call_center_structure.contract_types_num # number of contract types
        self.I = call_center_structure.agent_groups_num # number of agent groups
        self.agent_nodes = list(call_center_structure.G.nodes())[:self.K] # first K nodes are agent nodes
        self.customer_nodes = list(call_center_structure.G.nodes())[self.K:] # remain nodes are customer nodes
        self.calls_flow = {} # record the arrival time of each call
        self.service_flow = [] # record the call sorted by service finish time
        self.patience_flow = [] # record the call sorted by patience time 
        self.queue = {c: [] for c in self.customer_nodes}
        '''
            Counters:
                goodSL_num: number of served calls that have waited no more than AWT
                served_num: number of served calls
                abandoned_num: number of abandoned calls
                abandoned_afterAWT_num: number if abandoned calls after AWT
            Ratios:
                SL: service level, goodSL_num / (served_num + abandoned_afterAWT)
                abandon_ratio: abandoned_num / (served_num + abandoned_num)
                occupancy_ratio_unit: busy_agent_num / agent_num
                occupancy_ratio: sum(busy_agent_num) / (agent_num * T)
        '''
        self.goodSL_num = {c: 0 for c in self.customer_nodes}
        self.served_num = {c: 0 for c in self.customer_nodes}
        self.abandoned_num = {c: 0 for c in self.customer_nodes}
        self.abandoned_afterAWT_num = {c: 0 for c in self.customer_nodes}
        self.busy_agent_num = {s: [] for s in self.agent_nodes}
        self.SL = {c: [] for c in self.customer_nodes}
        self.abandon_ratio = {c: [] for c in self.customer_nodes}
        self.occupancy_ratio_unit = {s: [] for s in self.agent_nodes}
        self.occupancy_ratio = {s: 0 for s in self.agent_nodes}
        '''
            random generator, only support the specific (poisson, exponential, exponential) combination
        '''
        if self.structure.distribution['arrival'] == 'poisson':
            self.arrival_generator = np.random.exponential
        if self.structure.distribution['service'] == 'exponential':
            self.service_generator = np.random.exponential
        if self.structure.distribution['patience'] == 'exponential':
            self.patience_generator = np.random.exponential

        self.current_event = [] # record current arrival event and service event
        
        self.agent_groups = {}
        for i in range(self.I):
            name = self.agent_nodes[i]
            capacity = call_center_structure.G.nodes[name]['capacity']
            self.agent_groups[name] = ServiceTable(name, [Server(name, i) for i in range(capacity)])

    def clear(self):
        self.t = 0
        self.K = 0
        self.I = 0
        self.router = 'G'
        self.structure.clear()
        self.goodSL_num.clear()
        self.served_num.clear()
        self.abandoned_num.clear()
        self.abandoned_afterAWT_num.clear()
        self.busy_agent_num.clear()
        self.SL.clear()
        self.abandon_ratio.clear()
        self.occupancy_ratio.clear()

    def generate_calls_flow(self, call_flow_size):
        ''' generate call flow and convert it to second format'''
        for c in self.customer_nodes:
            intervals = self.arrival_generator(1 / self.structure.G.nodes[c]['lmbda'], (call_flow_size, ))
            arrival_time = np.round(intervals.cumsum() * 60)
            self.calls_flow[c] = arrival_time.astype(int).tolist()

    def check_arrival_event(self):
        for c in self.calls_flow:
            index = 0
            for i, arrival_time in enumerate(self.calls_flow[c]):
                if arrival_time <= self.t:
                    self.current_event.append(('arrival', c, arrival_time))
                else:
                    index = i
                    break
            self.calls_flow[c] = self.calls_flow[c][index :]

    def check_service_event(self):
        index = 0
        for i, S in enumerate(self.service_flow):
            if S.finish_time <= self.t:
                self.agent_groups[S.name].servers[S.index].finish_order()
                self.current_event.append(('service', S))
            else:
                index = i
                break
        self.service_flow = self.service_flow[index :]

    def check_abandon_event(self):
        index = 0
        for i, C in enumerate(self.patience_flow):
            if C.patience_time <= self.t:
                self.current_event.append(('patience', C))
            else:
                index = i
                break
        self.patience_flow = self.patience_flow[index :]

    def choose_server_byG(self, C, choices):
        '''select agent group with longest idle time(earlist last finish time)'''
        choices.sort(key=lambda x: self.agent_groups[x].last_finish_time)
        return choices[0]

    def choose_server(self, C):
        choices_ = list(self.structure.G[C.name])
        choices = []
        for v in choices_:
            if self.agent_groups[v].is_available:
                choices.append(v)
        if len(choices) == 0:
            return -1
        if len(choices) == 1:
            return choices[0]
        if self.router == 'G':
            return self.choose_server_byG(C, choices)
    
    def choose_customer_byG(self, S, choices):
        choices_ = []
        for c, lst in self.queue.items():
            if c in choices and len(lst) > 0:
                choices_.append((c, lst[0].arrival_time))
        if len(choices_) == 0:
            return -1
        else:
            choices_.sort(key=lambda x: x[1])
            return choices_[0][0]

    def choose_customer(self, S):
        choices = list(self.structure.G[S.name])
        if self.router == 'G':
            return self.choose_customer_byG(S, choices)
           
    def insert_into_service_flow(self, S):
        index = len(self.service_flow)
        for i, S_ in enumerate(self.service_flow):
            if S_.finish_time >= S.finish_time:
                index = i
                break
        self.service_flow.insert(index, S)

    def insert_into_patience_flow(self, C):
        index = len(self.patience_flow)
        for i, C_ in enumerate(self.patience_flow):
            if C_.patience_time >= C.patience_time:
                index = i
                break
        self.patience_flow.insert(index, C)

    def assign_customer_to_server(self, C, s):
        '''s is the agent group name'''
        # print('call %s is assigned to agent group %s' %(C.name, s))
        service_time = round(self.service_generator(1 / self.structure.G[s][C.name]['mu']) * 60)
        index = self.agent_groups[s].get_idlest_server_index()
        self.agent_groups[s].servers[index].receive_order(self.t, C.name, service_time)
        self.insert_into_service_flow(self.agent_groups[s].servers[index])
        self.agent_groups[s].add_busy_agent()

    def put_into_queue(self, C):
        c = C.name
        patience_time = round(self.patience_generator(1 / self.structure.G.nodes[c]['nu']) * 60)
        C.patience_time = self.t + patience_time
        self.queue[c].append(C) # don't consider queue capacity
        self.insert_into_patience_flow(C)

    def counter_update(self):
        for c in self.customer_nodes:
            if self.served_num[c] + self.abandoned_afterAWT_num[c] == 0:
                self.SL[c].append(1)
            else:
                self.SL[c].append(self.goodSL_num[c] / (self.served_num[c] + self.abandoned_afterAWT_num[c]))
            if self.served_num[c] + self.abandoned_num[c] == 0:
                self.abandon_ratio[c].append(1)
            else:
                self.abandon_ratio[c].append(self.abandoned_num[c] / (self.served_num[c] + self.abandoned_num[c]))
        for s in self.agent_nodes:
            self.busy_agent_num[s].append(self.agent_groups[s].busy_agent_num)
            self.occupancy_ratio_unit[s].append(self.agent_groups[s].busy_agent_num / self.agent_groups[s].n_servers)

    def performance_evaluation(self):
        for s in self.agent_nodes:
            self.occupancy_ratio[s] = sum(self.busy_agent_num[s]) / (self.agent_groups[s].n_servers*self.T)
        SL = {c: self.SL[c][-1] for c in self.customer_nodes}
        AR = {c: self.abandon_ratio[c][-1] for c in self.customer_nodes}
        OR = {s: self.occupancy_ratio[s] for s in self.agent_nodes}
        PE = F_s(SL, self.SL_threshold)
        return PE

    def step(self):
        self.current_event.clear()
        self.check_arrival_event()
        self.check_service_event()
        self.check_abandon_event()
        for event in self.current_event:
            if event[0] == 'arrival':
                C = Customer(event[1], event[2])
                s = self.choose_server(C)
                if s == -1:
                    self.put_into_queue(C)
                else:
                    self.assign_customer_to_server(C, s)
                    self.goodSL_num[C.name] += 1
                    self.served_num[C.name] += 1
            elif event[0] == 'service':
                S= event[1]
                self.agent_groups[S.name].sub_busy_agent()
                c = self.choose_customer(S)
                if c != -1:
                    C = self.queue[c][0]
                    self.served_num[c] += 1
                    waiting_time = self.t - C.arrival_time
                    if waiting_time <= self.AWT:
                        self.goodSL_num[c] += 1    
                    self.assign_customer_to_server(C, S.name)
                    self.queue[c].pop(0)
                else:
                    self.agent_groups[S.name].servers[S.index].finish_order()
            elif event[0] == 'abandon':
                C= event[1]
                self.abandoned_num[C.name] += 1
                waiting_time = self.t - C.arrival_time
                if waiting_time > self.AWT:
                    self.abandoned_afterAWT_num[C.name] += 1
                self.queue[C.name].remove(C)

    def run(self):
        self.generate_calls_flow(100000)
        for _ in tqdm(range(self.T)):
            self.step()
            self.counter_update()
            self.t += 1
        PE = self.performance_evaluation()
        print('Performance evaluation: ', PE)
        fig, ax = plt.subplots()
        for c in self.customer_nodes:
            ax.plot(self.SL[c], label=c)
        ax.set_xlabel('time')
        ax.set_ylabel('service level')
        ax.set_title('performance evaluation')
        ax.legend()
        plt.show()
          
