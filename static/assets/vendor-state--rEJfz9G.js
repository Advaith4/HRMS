import{a as e}from"./rolldown-runtime-Cyuzqnbw.js";import{f as t}from"./vendor-charts-DtgBfrS5.js";var n=e(t(),1),r={data:``},i=e=>{if(typeof window==`object`){let t=(e?e.querySelector(`#_goober`):window._goober)||Object.assign(document.createElement(`style`),{innerHTML:` `,id:`_goober`});return t.nonce=window.__nonce__,t.parentNode||(e||document.head).appendChild(t),t.firstChild}return e||r},a=/(?:([\u0080-\uFFFF\w-%@]+) *:? *([^{;]+?);|([^;}{]*?) *{)|(}\s*)/g,o=/\/\*[^]*?\*\/|  +/g,s=/\n+/g,c=(e,t)=>{let n=``,r=``,i=``;for(let a in e){let o=e[a];a[0]==`@`?a[1]==`i`?n=a+` `+o+`;`:r+=a[1]==`f`?c(o,a):a+`{`+c(o,a[1]==`k`?``:t)+`}`:typeof o==`object`?r+=c(o,t?t.replace(/([^,])+/g,e=>a.replace(/([^,]*:\S+\([^)]*\))|([^,])+/g,t=>/&/.test(t)?t.replace(/&/g,e):e?e+` `+t:t)):a):o!=null&&(a=a[1]==`-`?a:a.replace(/[A-Z]/g,`-$&`).toLowerCase(),i+=c.p?c.p(a,o):a+`:`+o+`;`)}return n+(t&&i?t+`{`+i+`}`:i)+r},l={},u=e=>{if(typeof e==`object`){let t=``;for(let n in e)t+=n+u(e[n]);return t}return e},d=(e,t,n,r,i)=>{let d=u(e),f=l[d]||(l[d]=(e=>{let t=0,n=11;for(;t<e.length;)n=101*n+e.charCodeAt(t++)>>>0;return`go`+n})(d));if(!l[f]){let t=d===e?(e=>{let t,n,r=[{}];for(;t=a.exec(e.replace(o,``));)t[4]?r.shift():t[3]?(n=t[3].replace(s,` `).trim(),r.unshift(r[0][n]=r[0][n]||{})):r[0][t[1]]=t[2].replace(s,` `).trim();return r[0]})(e):e;l[f]=c(i?{[`@keyframes `+f]:t}:t,n?``:`.`+f)}let p=n&&l.g;return n&&(l.g=l[f]),((e,t,n,r)=>{r?t.data=t.data.replace(r,e):t.data.indexOf(e)===-1&&(t.data=n?e+t.data:t.data+e)})(l[f],t,r,p),f},f=(e,t,n)=>e.reduce((e,r,i)=>{let a=t[i];if(a&&a.call){let e=a(n),t=e&&e.props&&e.props.className||/^go/.test(e)&&e;a=t?`.`+t:e&&typeof e==`object`?e.props?``:c(e,``):!1===e?``:e}return e+r+(a??``)},``);function p(e){let t=this||{},n=e.call?e(t.p):e;return d(n.unshift?n.raw?f(n,[].slice.call(arguments,1),t.p):n.reduce((e,n)=>Object.assign(e,n&&n.call?n(t.p):n),{}):n,i(t.target),t.g,t.o,t.k)}var m,h,g;p.bind({g:1});var _=p.bind({k:1});function v(e,t,n,r){c.p=t,m=e,h=n,g=r}function y(e,t){let n=this||{};return function(){let r=arguments;function i(a,o){let s=Object.assign({},a),c=s.className||i.className;n.p=Object.assign({theme:h&&h()},s),n.o=/go\d/.test(c),s.className=p.apply(n,r)+(c?` `+c:``),t&&(s.ref=o);let l=e;return e[0]&&(l=s.as||e,delete s.as),g&&l[0]&&g(s),m(l,s)}return t?t(i):i}}var ee=e=>typeof e==`function`,b=(e,t)=>ee(e)?e(t):e,x=(()=>{let e=0;return()=>(++e).toString()})(),S=(()=>{let e;return()=>{if(e===void 0&&typeof window<`u`){let t=matchMedia(`(prefers-reduced-motion: reduce)`);e=!t||t.matches}return e}})(),te=20,C=`default`,w=(e,t)=>{let{toastLimit:n}=e.settings;switch(t.type){case 0:return{...e,toasts:[t.toast,...e.toasts].slice(0,n)};case 1:return{...e,toasts:e.toasts.map(e=>e.id===t.toast.id?{...e,...t.toast}:e)};case 2:let{toast:r}=t;return w(e,{type:+!!e.toasts.find(e=>e.id===r.id),toast:r});case 3:let{toastId:i}=t;return{...e,toasts:e.toasts.map(e=>e.id===i||i===void 0?{...e,dismissed:!0,visible:!1}:e)};case 4:return t.toastId===void 0?{...e,toasts:[]}:{...e,toasts:e.toasts.filter(e=>e.id!==t.toastId)};case 5:return{...e,pausedAt:t.time};case 6:let a=t.time-(e.pausedAt||0);return{...e,pausedAt:void 0,toasts:e.toasts.map(e=>({...e,pauseDuration:e.pauseDuration+a}))}}},T=[],E={toasts:[],pausedAt:void 0,settings:{toastLimit:te}},D={},O=(e,t=C)=>{D[t]=w(D[t]||E,e),T.forEach(([e,n])=>{e===t&&n(D[t])})},k=e=>Object.keys(D).forEach(t=>O(e,t)),ne=e=>Object.keys(D).find(t=>D[t].toasts.some(t=>t.id===e)),A=(e=C)=>t=>{O(t,e)},re={blank:4e3,error:4e3,success:2e3,loading:1/0,custom:4e3},ie=(e={},t=C)=>{let[r,i]=(0,n.useState)(D[t]||E),a=(0,n.useRef)(D[t]);(0,n.useEffect)(()=>(a.current!==D[t]&&i(D[t]),T.push([t,i]),()=>{let e=T.findIndex(([e])=>e===t);e>-1&&T.splice(e,1)}),[t]);let o=r.toasts.map(t=>({...e,...e[t.type],...t,removeDelay:t.removeDelay||e[t.type]?.removeDelay||e?.removeDelay,duration:t.duration||e[t.type]?.duration||e?.duration||re[t.type],style:{...e.style,...e[t.type]?.style,...t.style}}));return{...r,toasts:o}},j=(e,t=`blank`,n)=>({createdAt:Date.now(),visible:!0,dismissed:!1,type:t,ariaProps:{role:`status`,"aria-live":`polite`},message:e,pauseDuration:0,...n,id:n?.id||x()}),M=e=>(t,n)=>{let r=j(t,e,n);return A(r.toasterId||ne(r.id))({type:2,toast:r}),r.id},N=(e,t)=>M(`blank`)(e,t);N.error=M(`error`),N.success=M(`success`),N.loading=M(`loading`),N.custom=M(`custom`),N.dismiss=(e,t)=>{let n={type:3,toastId:e};t?A(t)(n):k(n)},N.dismissAll=e=>N.dismiss(void 0,e),N.remove=(e,t)=>{let n={type:4,toastId:e};t?A(t)(n):k(n)},N.removeAll=e=>N.remove(void 0,e),N.promise=(e,t,n)=>{let r=N.loading(t.loading,{...n,...n?.loading});return typeof e==`function`&&(e=e()),e.then(e=>{let i=t.success?b(t.success,e):void 0;return i?N.success(i,{id:r,...n,...n?.success}):N.dismiss(r),e}).catch(e=>{let i=t.error?b(t.error,e):void 0;i?N.error(i,{id:r,...n,...n?.error}):N.dismiss(r)}),e};var P=1e3,F=(e,t=`default`)=>{let{toasts:r,pausedAt:i}=ie(e,t),a=(0,n.useRef)(new Map).current,o=(0,n.useCallback)((e,t=P)=>{if(a.has(e))return;let n=setTimeout(()=>{a.delete(e),s({type:4,toastId:e})},t);a.set(e,n)},[]);(0,n.useEffect)(()=>{if(i)return;let e=Date.now(),n=r.map(n=>{if(n.duration===1/0)return;let r=(n.duration||0)+n.pauseDuration-(e-n.createdAt);if(r<0){n.visible&&N.dismiss(n.id);return}return setTimeout(()=>N.dismiss(n.id,t),r)});return()=>{n.forEach(e=>e&&clearTimeout(e))}},[r,i,t]);let s=(0,n.useCallback)(A(t),[t]),c=(0,n.useCallback)(()=>{s({type:5,time:Date.now()})},[s]),l=(0,n.useCallback)((e,t)=>{s({type:1,toast:{id:e,height:t}})},[s]),u=(0,n.useCallback)(()=>{i&&s({type:6,time:Date.now()})},[i,s]),d=(0,n.useCallback)((e,t)=>{let{reverseOrder:n=!1,gutter:i=8,defaultPosition:a}=t||{},o=r.filter(t=>(t.position||a)===(e.position||a)&&t.height),s=o.findIndex(t=>t.id===e.id),c=o.filter((e,t)=>t<s&&e.visible).length;return o.filter(e=>e.visible).slice(...n?[c+1]:[0,c]).reduce((e,t)=>e+(t.height||0)+i,0)},[r]);return(0,n.useEffect)(()=>{r.forEach(e=>{if(e.dismissed)o(e.id,e.removeDelay);else{let t=a.get(e.id);t&&(clearTimeout(t),a.delete(e.id))}})},[r,o]),{toasts:r,handlers:{updateHeight:l,startPause:c,endPause:u,calculateOffset:d}}},I=_`
from {
  transform: scale(0) rotate(45deg);
	opacity: 0;
}
to {
 transform: scale(1) rotate(45deg);
  opacity: 1;
}`,L=_`
from {
  transform: scale(0);
  opacity: 0;
}
to {
  transform: scale(1);
  opacity: 1;
}`,R=_`
from {
  transform: scale(0) rotate(90deg);
	opacity: 0;
}
to {
  transform: scale(1) rotate(90deg);
	opacity: 1;
}`,z=y(`div`)`
  width: 20px;
  opacity: 0;
  height: 20px;
  border-radius: 10px;
  background: ${e=>e.primary||`#ff4b4b`};
  position: relative;
  transform: rotate(45deg);

  animation: ${I} 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)
    forwards;
  animation-delay: 100ms;

  &:after,
  &:before {
    content: '';
    animation: ${L} 0.15s ease-out forwards;
    animation-delay: 150ms;
    position: absolute;
    border-radius: 3px;
    opacity: 0;
    background: ${e=>e.secondary||`#fff`};
    bottom: 9px;
    left: 4px;
    height: 2px;
    width: 12px;
  }

  &:before {
    animation: ${R} 0.15s ease-out forwards;
    animation-delay: 180ms;
    transform: rotate(90deg);
  }
`,B=_`
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
`,V=y(`div`)`
  width: 12px;
  height: 12px;
  box-sizing: border-box;
  border: 2px solid;
  border-radius: 100%;
  border-color: ${e=>e.secondary||`#e0e0e0`};
  border-right-color: ${e=>e.primary||`#616161`};
  animation: ${B} 1s linear infinite;
`,H=_`
from {
  transform: scale(0) rotate(45deg);
	opacity: 0;
}
to {
  transform: scale(1) rotate(45deg);
	opacity: 1;
}`,U=_`
0% {
	height: 0;
	width: 0;
	opacity: 0;
}
40% {
  height: 0;
	width: 6px;
	opacity: 1;
}
100% {
  opacity: 1;
  height: 10px;
}`,W=y(`div`)`
  width: 20px;
  opacity: 0;
  height: 20px;
  border-radius: 10px;
  background: ${e=>e.primary||`#61d345`};
  position: relative;
  transform: rotate(45deg);

  animation: ${H} 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)
    forwards;
  animation-delay: 100ms;
  &:after {
    content: '';
    box-sizing: border-box;
    animation: ${U} 0.2s ease-out forwards;
    opacity: 0;
    animation-delay: 200ms;
    position: absolute;
    border-right: 2px solid;
    border-bottom: 2px solid;
    border-color: ${e=>e.secondary||`#fff`};
    bottom: 6px;
    left: 6px;
    height: 10px;
    width: 6px;
  }
`,G=y(`div`)`
  position: absolute;
`,K=y(`div`)`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-width: 20px;
  min-height: 20px;
`,q=_`
from {
  transform: scale(0.6);
  opacity: 0.4;
}
to {
  transform: scale(1);
  opacity: 1;
}`,J=y(`div`)`
  position: relative;
  transform: scale(0.6);
  opacity: 0.4;
  min-width: 20px;
  animation: ${q} 0.3s 0.12s cubic-bezier(0.175, 0.885, 0.32, 1.275)
    forwards;
`,Y=({toast:e})=>{let{icon:t,type:r,iconTheme:i}=e;return t===void 0?r===`blank`?null:n.createElement(K,null,n.createElement(V,{...i}),r!==`loading`&&n.createElement(G,null,r===`error`?n.createElement(z,{...i}):n.createElement(W,{...i}))):typeof t==`string`?n.createElement(J,null,t):t},ae=e=>`
0% {transform: translate3d(0,${e*-200}%,0) scale(.6); opacity:.5;}
100% {transform: translate3d(0,0,0) scale(1); opacity:1;}
`,oe=e=>`
0% {transform: translate3d(0,0,-1px) scale(1); opacity:1;}
100% {transform: translate3d(0,${e*-150}%,-1px) scale(.6); opacity:0;}
`,se=`0%{opacity:0;} 100%{opacity:1;}`,ce=`0%{opacity:1;} 100%{opacity:0;}`,le=y(`div`)`
  display: flex;
  align-items: center;
  background: #fff;
  color: #363636;
  line-height: 1.3;
  will-change: transform;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1), 0 3px 3px rgba(0, 0, 0, 0.05);
  max-width: 350px;
  pointer-events: auto;
  padding: 8px 10px;
  border-radius: 8px;
`,ue=y(`div`)`
  display: flex;
  justify-content: center;
  margin: 4px 10px;
  color: inherit;
  flex: 1 1 auto;
  white-space: pre-line;
`,de=(e,t)=>{let n=e.includes(`top`)?1:-1,[r,i]=S()?[se,ce]:[ae(n),oe(n)];return{animation:t?`${_(r)} 0.35s cubic-bezier(.21,1.02,.73,1) forwards`:`${_(i)} 0.4s forwards cubic-bezier(.06,.71,.55,1)`}},fe=n.memo(({toast:e,position:t,style:r,children:i})=>{let a=e.height?de(e.position||t||`top-center`,e.visible):{opacity:0},o=n.createElement(Y,{toast:e}),s=n.createElement(ue,{...e.ariaProps},b(e.message,e));return n.createElement(le,{className:e.className,style:{...a,...r,...e.style}},typeof i==`function`?i({icon:o,message:s}):n.createElement(n.Fragment,null,o,s))});v(n.createElement);var pe=({id:e,className:t,style:r,onHeightUpdate:i,children:a})=>{let o=n.useCallback(t=>{if(t){let n=()=>{let n=t.getBoundingClientRect().height;i(e,n)};n(),new MutationObserver(n).observe(t,{subtree:!0,childList:!0,characterData:!0})}},[e,i]);return n.createElement(`div`,{ref:o,className:t,style:r},a)},me=(e,t)=>{let n=e.includes(`top`),r=n?{top:0}:{bottom:0},i=e.includes(`center`)?{justifyContent:`center`}:e.includes(`right`)?{justifyContent:`flex-end`}:{};return{left:0,right:0,display:`flex`,position:`absolute`,transition:S()?void 0:`all 230ms cubic-bezier(.21,1.02,.73,1)`,transform:`translateY(${t*(n?1:-1)}px)`,...r,...i}},he=p`
  z-index: 9999;
  > * {
    pointer-events: auto;
  }
`,X=16,Z=({reverseOrder:e,position:t=`top-center`,toastOptions:r,gutter:i,children:a,toasterId:o,containerStyle:s,containerClassName:c})=>{let{toasts:l,handlers:u}=F(r,o);return n.createElement(`div`,{"data-rht-toaster":o||``,style:{position:`fixed`,zIndex:9999,top:X,left:X,right:X,bottom:X,pointerEvents:`none`,...s},className:c,onMouseEnter:u.startPause,onMouseLeave:u.endPause},l.map(r=>{let o=r.position||t,s=me(o,u.calculateOffset(r,{reverseOrder:e,gutter:i,defaultPosition:t}));return n.createElement(pe,{id:r.id,key:r.id,onHeightUpdate:u.updateHeight,className:r.visible?he:``,style:s},r.type===`custom`?b(r.message,r):a?a(r):n.createElement(fe,{toast:r,position:o}))}))},ge=N,Q=e=>{let t,n=new Set,r=(e,r)=>{let i=typeof e==`function`?e(t):e;if(!Object.is(i,t)){let e=t;t=r??(typeof i!=`object`||!i)?i:Object.assign({},t,i),n.forEach(n=>n(t,e))}},i=()=>t,a={setState:r,getState:i,getInitialState:()=>o,subscribe:e=>(n.add(e),()=>n.delete(e))},o=t=e(r,i,a);return a},_e=(e=>e?Q(e):Q),ve=e=>e;function ye(e,t=ve){let r=n.useSyncExternalStore(e.subscribe,n.useCallback(()=>t(e.getState()),[e,t]),n.useCallback(()=>t(e.getInitialState()),[e,t]));return n.useDebugValue(r),r}var $=e=>{let t=_e(e),n=e=>ye(t,e);return Object.assign(n,t),n},be=(e=>e?$(e):$);export{Z as n,ge as r,be as t};