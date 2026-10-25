(function(){
  'use strict';
  const root=document.getElementById('zvChat'); if(!root) return;
  const launch=document.getElementById('zvChatLaunch'), panel=document.getElementById('zvChatPanel'), close=document.getElementById('zvChatClose');
  const body=document.getElementById('zvChatBody'), form=document.getElementById('zvChatForm'), input=document.getElementById('zvChatInput'), email=document.getElementById('zvChatEmail');
  const quick=document.getElementById('zvChatQuick'), lead=document.getElementById('zvChatLead'), inquiry=document.getElementById('zvChatInquiry');
  function open(){panel.classList.add('open');panel.setAttribute('aria-hidden','false');setTimeout(()=>input&&input.focus(),80)}
  function shut(){panel.classList.remove('open');panel.setAttribute('aria-hidden','true')}
  function bubble(text,type){const d=document.createElement('div');d.className='zv-chat-bubble '+type;d.textContent=text;body.appendChild(d);body.scrollTop=body.scrollHeight}
  function csrf(){const m=document.cookie.match(/csrftoken=([^;]+)/);return m?decodeURIComponent(m[1]):''}
  async function ask(message){if(!message)return;bubble(message,'user');input.value='';try{const r=await fetch(root.dataset.messageUrl || '/zenvibe/api/chatbot/message/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify({message,email:email&&email.value||''})});const data=await r.json();bubble(data.reply||'Sorry, I could not answer that right now.','bot');if(data.needs_email&&email){email.hidden=false;email.focus()}if(data.fallback&&lead)lead.style.display='block'}catch(e){bubble('The chat service is temporarily unavailable. Please contact info@zenvibe.ca.','bot')}}
  launch.addEventListener('click',()=>panel.classList.contains('open')?shut():open()); close&&close.addEventListener('click',shut);
  form&&form.addEventListener('submit',e=>{e.preventDefault();ask((input.value||'').trim())});
  quick&&quick.addEventListener('click',e=>{const b=e.target.closest('[data-q]');if(b)ask(b.dataset.q)});
  lead&&lead.addEventListener('click',()=>{inquiry.hidden=!inquiry.hidden;if(!inquiry.hidden)inquiry.querySelector('input,textarea')?.focus()});
  inquiry&&inquiry.addEventListener('submit',async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(inquiry).entries());data.page_url=location.href;try{const r=await fetch(root.dataset.inquiryUrl || '/zenvibe/api/chatbot/inquiry/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify(data)});const j=await r.json();if(j.ok){bubble(j.reply||'Thanks — we have your message.','bot');inquiry.reset();inquiry.hidden=true}}catch(err){bubble('Could not save your enquiry. Please email info@zenvibe.ca.','bot')}});
  window.zvOpenChat=open;
})();
