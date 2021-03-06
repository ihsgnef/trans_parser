from arc_standard import ArcStandard
from arc_eager import ArcEager
from parser import SimpleParser
import feature_extractor as fx
from train import main

if __name__ == '__main__':
    arcsys = ArcStandard()
    parser = SimpleParser(arcsys, fx.baseline, arcsys.static_oracle)
    main(arcsys, parser, False)
