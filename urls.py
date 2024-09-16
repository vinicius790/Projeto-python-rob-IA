from django.urls import path
from . import views

app_name = 'pagamentos'

urlpatterns = [
    # Página inicial do aplicativo
    path('', views.index, name='index'),

    # Listagem de pagamentos
    path('pagamentos/', views.pagamento_list, name='pagamento_list'),

    # Detalhes de um pagamento específico
    path('pagamentos/<int:id>/', views.pagamento_detail, name='pagamento_detail'),

    # Criar um novo pagamento
    path('pagamentos/novo/', views.pagamento_create, name='pagamento_create'),

    # Atualizar um pagamento existente
    path('pagamentos/<int:id>/editar/', views.pagamento_update, name='pagamento_update'),

    # Excluir um pagamento
    path('pagamentos/<int:id>/excluir/', views.pagamento_delete, name='pagamento_delete'),
]

