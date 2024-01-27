# -*- coding: utf-8 -*-
from kubernetes.client import api_client
from kubernetes.client.apis import core_v1_api
from kubernetes import client, config
import json
import yaml


class KubernetesTools(object):
    def __init__(self):
        self.k8s_url = 'https://10.20.1.40:6443'

    def get_token(self):
        """
        获取token
        :return:
        """
        with open('kube/auth/token.txt', 'r') as file:
            Token = file.read().strip('\n')
            return Token

    def get_api(self, api_type="core"):
        """
        获取API的CoreV1Api版本对象
        :return:
        """
        configuration = client.Configuration()
        configuration.host = self.k8s_url
        configuration.verify_ssl = False
        configuration.api_key = {"authorization": "Bearer " + self.get_token()}
        client1 = api_client.ApiClient(configuration=configuration)
        if api_type == "core":
            api = core_v1_api.CoreV1Api(client1)
        else:
            api = client.AppsV1Api(client1)
        return api

    def get_namespace_list(self):
        """
        获取命名空间列表
        :return:
        """
        api = self.get_api()
        namespace_list = []
        for ns in api.list_namespace().items:
            # print(ns.metadata.name)
            namespace_list.append(ns.metadata.name)

        return namespace_list

    def get_node(self):
        api = self.get_api()
        result = api.list_node()
        return result

    def list_node(self):
        api = self.get_api()
        api_response = api.list_node()
        data = {}
        for i in api_response.items:
            data[i.metadata.name] = {"name": i.metadata.name,
                                     "status": i.status.conditions[-1].type if i.status.conditions[
                                                                                   -1].status == "True" else "NotReady",
                                     "ip": i.status.addresses[0].address,
                                     "kubelet_version": i.status.node_info.kubelet_version,
                                     "os_image": i.status.node_info.os_image,
                                     }
        return data

    def list_pod(self):
        api = self.get_api()
        api_response = api.list_pod_for_all_namespaces()
        data = {}
        for i in api_response.items:
            data[i.metadata.name] = {"ip": i.status.pod_ip, "namespace": i.metadata.namespace}
        return data

    def create_pod(self, body, namespace='default'):
        api = self.get_api("core")
        api.create_namespaced_pod(body=body, namespace=namespace)

    def create_deployment(self, body, namespace='default'):
        api = self.get_api("app")
        api.create_namespaced_deployment(body=body, namespace=namespace)

    def delete_pod(self, name, namespace='default'):
        api = self.get_api()
        api.delete_namespaced_pod(name, namespace)

    def delete_deployment(self, name, namespace='default'):
        api = self.get_api("app")
        api.delete_namespaced_deployment(name, namespace)

if __name__ == '__main__':
    # namespace_list = KubernetesTools().get_namespace_list()
    # print(namespace_list)
    result = KubernetesTools().list_pod()
    # result = yaml.load(result, Loader=yaml.SafeLoader)
    print(json.dumps(result, indent=4))
