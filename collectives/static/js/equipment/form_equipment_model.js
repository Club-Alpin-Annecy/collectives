const btn_display_form_model = document.querySelector('#btn_display_form_model');
const form_model = document.querySelector('.form_model');

btn_display_form_model.addEventListener('click', ()=> {
    form_model.classList.toggle('display-none');
})
