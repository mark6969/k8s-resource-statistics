from .models import Document, Capacity
from .k8s import KubernetesTools
from django.shortcuts import render
from django.http import HttpResponse
from django.db import connection

import yaml
import json
import re


def upload_file(request):
    if request.method == "POST":
        uploaded_file = request.FILES["uploadedFile"]

        file = uploaded_file.read().decode('utf-8')
        file = yaml.load(file, Loader=yaml.SafeLoader)
        try:
            name, type, team, cpu_size, memory_size, namespace = check_and_get(file)
        except:
            return HttpResponse("error")
        name_type = "%s-%s" % (name, type)
        capacity = list(Capacity.objects.filter(team=team).values('cpu_size', 'memory_size'))
        if capacity:
            capacity = capacity[0]
            cpu_total_size = capacity.get('cpu_size')
            memory_total_size = capacity.get('memory_size')
        else:
            return HttpResponse("查無此team")

        if Document.objects.filter(name_type=name_type):
            return HttpResponse("名稱重複")

        if cpu_total_size > cpu_size and memory_total_size > memory_size:
            cpu_total_size -= cpu_size
            memory_total_size -= memory_size
        else:
            return HttpResponse("資源不足")

        k8s = KubernetesTools()
        if not namespace:
            namespace = 'default'
        try:
            if type == "Pod":
                k8s.create_pod(file, namespace)
            else:
                k8s.create_deployment(file, namespace)
        except:
            return HttpResponse("部屬失敗")

        document = Document(
            imac_team=team,
            uploadedFile=uploaded_file,
            cpu_size=cpu_size,
            memory_size=memory_size,
            name_type=name_type
        )
        document.save()

        capacity = Capacity(
            team=team,
            cpu_size=cpu_total_size,
            memory_size=memory_total_size
        )
        capacity.save()

    # documents = models.Document.objects.all()
    return HttpResponse("ooo")
    # return render(request, "Core/upload-file.html", context={
    #     "files": documents
    # })


def check_and_get(file):
    cpu_size = 0
    memory_size = 0
    replicas = 1
    kind = file.get("kind")
    metadata = file.get("metadata")
    if metadata:
        labels = metadata.get("labels")
        name = metadata.get("name")
        namespace = metadata.get("namespace")
        if not name:
            print("metadata裡缺少name")
            return HttpResponse("metadata裡缺少name")
        if labels:
            team = labels.get("app")
            if not team:
                print("labels裡缺少app")
                return HttpResponse("labels裡缺少app")
        else:
            print("metadata裡缺少labels")
            return HttpResponse("metadata裡缺少labels")
    else:
        print("缺少metadata欄位")
        return HttpResponse("缺少metadata欄位")

    spec = file.get("spec")
    if spec:
        if kind == "Pod":
            containers = spec.get("containers")
            if not containers:
                print("缺少containers或為空")
                return HttpResponse("缺少containers或為空")
        elif kind == "Deployment":
            replicas = spec.get("replicas")
            if not replicas:
                print("缺少replicas或為空")
                return HttpResponse("缺少replicas或為空")
            print(json.dumps(spec, indent=4))
            template = spec.get("template")
            if template:
                spec = template.get("spec")
                if spec:
                    containers = spec.get("containers")
                    if not containers:
                        print("缺少containers或為空")
                        return HttpResponse("缺少containers或為空")
                else:
                    print("缺少spec欄位")
                    return HttpResponse("缺少spec欄位")
            else:
                print("缺少template欄位")
                return HttpResponse("缺少template欄位")
        else:
            print("須為Pod or Deployment")
            return HttpResponse("須為Pod or Deployment")
    else:
        print("缺少spec欄位")
        return HttpResponse("缺少spec欄位")

    for container in containers:
        resources = container.get("resources")
        if resources:
            limits = resources.get("limits")
            if limits:
                cpu = limits.get("cpu")
                memory = limits.get("memory")
                if not cpu and memory:
                    print("cpu_size, memory_size 不可為空")
                    return HttpResponse("cpu_size, memory_size 不可為空")
                try:
                    size, cpu_unit = re.findall(r'^(\d+(?:\.\d+)?)(\w+)$', cpu)[0]
                except:
                    print("格式錯誤")
                    return HttpResponse("格式錯誤")
                if cpu_unit != "m":
                    print("cpu的單位用m")
                    return HttpResponse("cpu的單位用m")
                if not size:
                    print("大小不可為0")
                    return HttpResponse("大小不可為0")
                cpu_size += int(size)
                try:
                    size, memory_unit = re.findall(r'^(\d+(?:\.\d+)?)(\w+)$', memory)[0]
                except:
                    print("格式錯誤")
                    return HttpResponse("格式錯誤")
                if memory_unit != "Mi":
                    print("memory的單位用Mi")
                    return HttpResponse("memory的單位用Mi")
                if not size:
                    print("大小不可為0")
                    return HttpResponse("大小不可為0")
                memory_size += int(size)
            else:
                print("缺少limits欄位")
                return HttpResponse("缺少limits欄位")
        else:
            print("缺少resources欄位")
            return HttpResponse("缺少resources欄位")
    return name, kind, team, cpu_size*replicas, memory_size*replicas, namespace


def view_all(request):
    k8s = KubernetesTools()
    result = k8s.list_pod()
    return HttpResponse(json.dumps(result, indent=4))


def delete(request):
    name = request.POST.get('name')
    k8s_type = request.POST.get('type')
    if not name and k8s_type:
        return HttpResponse("請輸入name and type")
    if k8s_type not in ['Pod', 'Deployment']:
        return HttpResponse("type 須為 Pod or Deployment")
    name_type = "%s-%s" % (name, k8s_type)
    try:
        document = Document.objects.get(name_type=name_type)
    except:
        return HttpResponse("查無此資料")

    team = document.imac_team
    capacity = list(Capacity.objects.filter(team=team).values('cpu_size', 'memory_size'))
    if capacity:
        capacity = capacity[0]
        cpu_total_size = capacity.get('cpu_size')
        memory_total_size = capacity.get('memory_size')
    cpu_total_size += document.cpu_size
    memory_total_size += document.memory_size

    k8s = KubernetesTools()
    if k8s_type == "Pod":
        k8s.delete_pod(name)
    else:
        k8s.delete_deployment(name)
    capacity = Capacity(
        team=team,
        cpu_size=cpu_total_size,
        memory_size=memory_total_size
    )
    capacity.save()
    document.delete()
    return HttpResponse("刪除成功")
