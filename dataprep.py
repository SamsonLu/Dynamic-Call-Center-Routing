import yaml
import os

FILE_PATH = os.path.dirname(__file__)
FILE_NAME_PATH = os.path.split(os.path.realpath(__file__))[0]

def read_data(design_name):
    '''
        从config文件夹中读取数据，返回服务台人数，到达率，服务率，放弃率（均为list类型）构成的dict变量记为struct_data
        注：service_rate若为-1则表示该服务台不能服务该类型顾客
        到达率放弃率均为poison分布，服务率为exponential分布，后续需要添加不同分布的配置
        e.g.
        服务台人数： [90, 14]
        到达率： [18.0, 1.8]
        服务率： [[0.198, 0.18], [0.162, 0.18]]
        放弃率： [0.12, 0.24]
    '''
    yaml_path = os.path.join(FILE_NAME_PATH, f'config\\{design_name}_data.yaml')
    with open(yaml_path, 'r') as f:
        loader = f.read()
        data = yaml.load(loader)
        servers_table = data['s']
        arrival_rates = data['c']
        service_rates = data['mu']
        patience = data['v']
    struct_data = {'servers_table': servers_table, 'arrival_rates': arrival_rates, 'service_rates': service_rates, 'patience': patience}
    return struct_data


if __name__ == "__main__":
    design_name = 'Xdesign'
    struct_data= read_data(design_name)
    print('服务台人数：', struct_data['servers_table'])
    print('到达率：', struct_data['arrival_rates']['args'])
    print('服务率：', struct_data['service_rates']['args'])
    print('放弃率：', struct_data['patience']['args'])



