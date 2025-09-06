from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required



from .models import Cliente
from .forms import ClienteForm, ClienteSearchForm

class ClienteListView(ListView):
    model = Cliente
    template_name = 'clientes/lista_clientes.html'
    context_object_name = 'clientes'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        search_query = self.request.GET.get('q', '')
        categoria = self.request.GET.get('categoria', '')
        activo = self.request.GET.get('activo', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(nombre__icontains=search_query) |
                Q(correo_electronico__icontains=search_query)
            )
        
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        
        if activo:
            queryset = queryset.filter(activo=(activo.lower() == 'true'))
            
        return queryset.order_by('nombre')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ClienteSearchForm(self.request.GET or None)
        context['search_query'] = self.request.GET.get('q', '')
        context['categoria_filtro'] = self.request.GET.get('categoria', '')
        context['activo_filtro'] = self.request.GET.get('activo', '')
        return context

class ClienteDetailView(DetailView):
    model = Cliente
    template_name = 'clientes/detalle_cliente.html'
    context_object_name = 'cliente'
    
    def get_object(self, queryset=None):
        return get_object_or_404(Cliente, id_cliente=self.kwargs['pk'])

class ClienteCreateView(CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'clientes/formulario_cliente.html'
    
    def get_success_url(self):
        messages.success(self.request, _('Cliente creado exitosamente'))
        return reverse('clientes:detalle', kwargs={'pk': self.object.id_cliente})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        return response

class ClienteUpdateView(UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'clientes/formulario_cliente.html'
    
    def get_object(self, queryset=None):
        return get_object_or_404(Cliente, id_cliente=self.kwargs['pk'])
    
    def get_success_url(self):
        messages.success(self.request, _('Cliente actualizado exitosamente'))
        return reverse('clientes:detalle', kwargs={'pk': self.object.id_cliente})

class ClienteDeleteView(DeleteView):
    model = Cliente
    template_name = 'clientes/confirmar_eliminacion.html'
    success_url = reverse_lazy('clientes:lista')
    
    def get_object(self, queryset=None):
        return get_object_or_404(Cliente, id_cliente=self.kwargs['pk'])
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Cliente eliminado exitosamente'))
        return super().delete(request, *args, **kwargs)


def es_admin(user):
    return user.is_authenticated and user.is_staff

# --- Vista protegida ---
@login_required
def toggle_cliente_estado(request, pk):
    cliente = get_object_or_404(Cliente, id_cliente=pk)
    cliente.activo = not cliente.activo
    cliente.save()
    
    action = "activado" if cliente.activo else "desactivado"
    messages.success(request, f'Cliente {action} exitosamente')
    
    return redirect('clientes:lista')