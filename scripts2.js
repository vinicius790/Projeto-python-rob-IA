// scripts.js
document.addEventListener("DOMContentLoaded", function() {
    function fetchColaboradores() {
        fetch('/api/colaboradores')
            .then(response => response.json())
            .then(data => {
                const list = document.getElementById('colaboradores-list');
                list.innerHTML = '';  // Limpar a lista antes de adicionar novos itens
                data.forEach(colaborador => {
                    const li = document.createElement('li');
                    li.textContent = `${colaborador.nome} (${colaborador.cpf})`;
                    list.appendChild(li);
                });
            })
            .catch(error => console.error('Error fetching colaboradores:', error));
    }

    fetchColaboradores();

    // Form validation
    document.getElementById('colaboradorForm').addEventListener('submit', function(event) {
        const form = event.target;
        let isValid = true;
        const formData = new FormData(form);
        const nome = formData.get('nome');
        const cpf = formData.get('cpf');

        // Clear previous errors
        document.querySelectorAll('.error-message').forEach(e => e.remove());

        if (!nome) {
            isValid = false;
            showError('nome', 'O nome é obrigatório.');
        }

        if (!cpf || !/^\d{11}$/.test(cpf)) {
            isValid = false;
            showError('cpf', 'O CPF deve ter 11 dígitos numéricos.');
        }

        if (!isValid) {
            event.preventDefault();  // Prevent form submission
        }
    });

    function showError(fieldId, message) {
        const field = document.getElementById(fieldId);
        const error = document.createElement('div');
        error.className = 'error-message';
        error.textContent = message;
        field.parentNode.appendChild(error);
    }
});
