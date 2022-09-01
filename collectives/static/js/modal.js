

function openModal(modal)
{
    modal.classList.add('display-flex');
    modal.classList.remove('display-none');
    document.body.classList.add('overflow-hidden');
    document.body.classList.remove('overflow-visible');
}

function closeModal(modal)
{
    modal.classList.add('display-none');
    modal.classList.remove('display-flex');
    document.body.classList.add('overflow-visible');
    document.body.classList.remove('overflow-hidden');
}

document.addEventListener('DOMContentLoaded', ()=> {

    const modal = document.querySelector('.container_bg_modal');

    const btnOpenModal = document.querySelector('.button-open-modal');
    if(btnOpenModal) {
        btnOpenModal.addEventListener('click', ()=> {
            openModal(modal);
        });
    }

    const btnCloseModal = document.querySelector('.container_close');
    if(btnCloseModal) {
        btnCloseModal.addEventListener('click', ()=> {
            closeModal(modal);
        });
    }

})

