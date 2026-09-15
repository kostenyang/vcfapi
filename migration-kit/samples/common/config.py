"""讀組態。優先序：環境變數 VCF_API_CONFIG > 套件內 config.yaml > config.example.yaml。

憑證只從組態檔來，不寫死在程式裡，也不印出來。
"""
import os

import yaml

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _path():
    env = os.environ.get("VCF_API_CONFIG")
    if env:
        return env
    local = os.path.join(HERE, "config.yaml")
    if os.path.exists(local):
        return local
    return os.path.join(HERE, "config.example.yaml")


def load():
    with open(_path()) as fh:
        return yaml.safe_load(fh)


def get(section):
    cfg = load()
    if section not in cfg:
        raise SystemExit(
            "組態缺少 [%s]；請複製 config.example.yaml 成 config.yaml 後補上，"
            "或用 VCF_API_CONFIG 指向既有的 lab.yaml。" % section
        )
    return cfg[section], cfg.get("verify_tls", False)
