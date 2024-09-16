import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import Colaborador, Pagamento
from .forms import PagamentoForm  # Supondo que você tenha um formulário para Pagamento

# Funções para Django

def index(request):
    return render(request, 'pagamentos/index.html')

def pagamento_list(request):
    pagamentos = Pagamento.objects.all()
    return render(request, 'pagamentos/pagamento_list.html', {'pagamentos': pagamentos})

def pagamento_detail(request, id):
    pagamento = get_object_or_404(Pagamento, id=id)
    return render(request, 'pagamentos/pagamento_detail.html', {'pagamento': pagamento})

def pagamento_create(request):
    if request.method == 'POST':
        form = PagamentoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('pagamentos:pagamento_list')
    else:
        form = PagamentoForm()
    return render(request, 'pagamentos/pagamento_form.html', {'form': form})

def pagamento_update(request, id):
    pagamento = get_object_or_404(Pagamento, id=id)
    if request.method == 'POST':
        form = PagamentoForm(request.POST, instance=pagamento)
        if form.is_valid():
            form.save()
            return redirect('pagamentos:pagamento_list')
    else:
        form = PagamentoForm(instance=pagamento)
    return render(request, 'pagamentos/pagamento_form.html', {'form': form})

def pagamento_delete(request, id):
    pagamento = get_object_or_404(Pagamento, id=id)
    if request.method == 'POST':
        pagamento.delete()
        return redirect('pagamentos:pagamento_list')
    return render(request, 'pagamentos/pagamento_confirm_delete.html', {'pagamento': pagamento})

def lista_colaboradores(request):
    colaboradores = Colaborador.objects.all()
    return render(request, 'pagamentos/lista_colaboradores.html', {'colaboradores': colaboradores})

def colaboradores_api(request):
    """Retornar a lista de colaboradores em formato JSON."""
    try:
        colaboradores = Colaborador.objects.all()
        result = [{'nome': c.nome, 'cpf': c.cpf} for c in colaboradores]
        return JsonResponse(result, safe=False)
    except Exception as e:
        logging.error(f"Erro ao buscar colaboradores: {e}")
        return JsonResponse({'error': 'Erro ao buscar colaboradores'}, status=500)

def add_pagamento_api(request):
    """Adicionar um pagamento ao banco de dados via API."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            colaborador = Colaborador.objects.filter(cpf=data['cpf']).first()
            if not colaborador:
                return JsonResponse({'error': 'Colaborador não encontrado'}, status=404)
            pagamento = Pagamento(
                colaborador=colaborador,
                valor=data.get('valor', 0),
                data=data['data_pagamento']
            )
            pagamento.save()
            return JsonResponse({'message': 'Pagamento adicionado com sucesso!'}, status=201)
        except Exception as e:
            logging.error(f"Erro ao adicionar pagamento: {e}")
            return JsonResponse({'error': 'Erro ao adicionar pagamento'}, status=500)
    return JsonResponse({'error': 'Método não permitido'}, status=405)

# Django URLs
from django.urls import path

urlpatterns = [
    path('', index, name='index'),
    path('pagamentos/', pagamento_list, name='pagamento_list'),
    path('pagamentos/<int:id>/', pagamento_detail, name='pagamento_detail'),
    path('pagamentos/novo/', pagamento_create, name='pagamento_create'),
    path('pagamentos/<int:id>/editar/', pagamento_update, name='pagamento_update'),
    path('pagamentos/<int:id>/excluir/', pagamento_delete, name='pagamento_delete'),
    path('colaboradores/', lista_colaboradores, name='lista_colaboradores'),
    path('api/colaboradores/', colaboradores_api, name='colaboradores_api'),
    path('api/pagamentos/', add_pagamento_api, name='add_pagamento_api'),
]
