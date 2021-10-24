


document.addEventListener('DOMContentLoaded', ()=> {

    const body = document.querySelector('body');

    const btnOpenModal = document.querySelector('.button-open-modal');
    const btnCloseModal = document.querySelector('.container_close');

    const modal = document.querySelector('.container_bg_modal');


    btnOpenModal.addEventListener('click', ()=> {
        modal.classList.add('display-flex');
        modal.classList.remove('display-none');


        body.classList.add('overflow-hidden');
        body.classList.remove('overflow-visible');
    })


    btnCloseModal.addEventListener('click', ()=> {
        modal.classList.add('display-none');
        modal.classList.remove('display-flex');

        body.classList.add('overflow-visible');
        body.classList.remove('overflow-hidden');
        
    })




})

