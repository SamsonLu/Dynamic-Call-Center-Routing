import argparse



def mysum(x, y):
    return x + y

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-x', type=float, default=0)
    parser.add_argument('-y', type=float, default=0)
    args = parser.parse_args()
    s = mysum(args.x, args.y)
    print(s)