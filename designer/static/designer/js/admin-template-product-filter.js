(function(){
  function init(){
    const category=document.getElementById('id_category_filter');
    const product=document.getElementById('id_product');
    if(!category||!product)return;
    let mapping={};
    try{mapping=JSON.parse(product.getAttribute('data-category-map')||'{}');}catch(e){}
    const original=Array.from(product.options).map(o=>({value:o.value,text:o.text,disabled:o.disabled}));
    function refresh(){
      const selected=product.value;
      const cat=category.value;
      product.replaceChildren();
      original.forEach(item=>{
        if(item.value && cat && mapping[item.value]!==cat)return;
        const opt=new Option(item.text,item.value);
        opt.disabled=item.disabled;
        product.add(opt);
      });
      if(Array.from(product.options).some(o=>o.value===selected))product.value=selected;
      else product.value='';
    }
    category.addEventListener('change',refresh);
    refresh();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);
  else init();
})();
