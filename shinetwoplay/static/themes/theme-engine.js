/**
 * ShineTwoPlay Theme Engine
 * Zero-downtime, purely frontend via CSS custom property overrides.
 */

window.ThemeEngine = {
    DEFAULT: 'light',
    STORAGE_KEY: 's2p-theme',
    
    THEMES: [
        { id: 'light',   emoji: '☀️', name: 'Light',   baseDesc: 'Sunshine Yellow / Warm Cream', swatches: ['#FFD93D', '#FFB84D', '#FFFAEF', '#4A3F35'] },
        { id: 'dark',    emoji: '🌙', name: 'Dark',    baseDesc: 'Catppuccin Mocha', swatches: ['#1E1E2E', '#F9E2AF', '#CBA6F7', '#CDD6F4'] },
        { id: 'love',    emoji: '💕', name: 'Love',    baseDesc: 'Rosé Pine inspired', swatches: ['#FFF0F5', '#FF79A8', '#FF4D8D', '#54273E'] },
        { id: 'galaxy',  emoji: '🌌', name: 'Galaxy',  baseDesc: 'Deep space navy + Milky Way', swatches: ['#020816', '#1D4ED8', '#60A5FA', '#FDE68A'] },
        { id: 'panda',   emoji: '🐼', name: 'Panda',   baseDesc: 'Bamboo Green', swatches: ['#F0FFF4', '#52B788', '#2D9A5F', '#1A3A2A'] },
        { id: 'penguin', emoji: '🐧', name: 'Penguin', baseDesc: 'Nord — icy arctic blue', swatches: ['#EAF4FD', '#5DADE2', '#2E86C1', '#1B2D40'] },
        { id: 'sunset',  emoji: '🌅', name: 'Sunset',  baseDesc: 'Deep Orange / Crimson', swatches: ['#FFF1E6', '#FF7043', '#E64A19', '#3D1A08'] },
        { id: 'neon',    emoji: '⚡', name: 'Neon',    baseDesc: 'Tokyo Night — cyberpunk', swatches: ['#0A0E1A', '#00E5FF', '#D500F9', '#76FF03'] }
    ],

    init: function() {
        // Read theme from localStorage immediately
        const savedTheme = localStorage.getItem(this.STORAGE_KEY) || this.DEFAULT;
        this.apply(savedTheme, false);

        // Render picker on window load so it doesn't block rendering
        window.addEventListener('load', () => {
            this.injectPickerUI();
            this.initCanvasBackground();
        });
    },

    apply: function(themeId, save = true) {
        document.documentElement.setAttribute('data-theme', themeId);
        if (save) {
            localStorage.setItem(this.STORAGE_KEY, themeId);
        }
        if (this.canvasInitialized) {
            this.renderCanvasBackground(themeId);
        }
    },

    get: function() {
        return localStorage.getItem(this.STORAGE_KEY) || this.DEFAULT;
    },

    injectPickerUI: function() {
        // Build generic picker button and modal into DOM
        const body = document.body;
        if (!body || document.getElementById('s2p-theme-panel')) return;

        // The Modal Overlay
        const overlay = document.createElement('div');
        overlay.id = 's2p-theme-overlay';
        overlay.className = 'theme-engine-overlay';
        overlay.onclick = () => this.closePicker();

        // The Panel
        const panel = document.createElement('div');
        panel.id = 's2p-theme-panel';
        panel.className = 'theme-engine-panel';
        
        let html = `
            <div class="theme-panel-header">
                <h3>🎨 Select Theme</h3>
                <button onclick="window.ThemeEngine.closePicker()" class="theme-close-btn">×</button>
            </div>
            <div class="theme-grid">
        `;

        const curr = this.get();
        this.THEMES.forEach(t => {
            const isSel = t.id === curr ? 'selected' : '';
            const swatchesHtml = t.swatches.map(c => `<div class="theme-swatch" style="background:${c}"></div>`).join('');
            
            html += `
                <div class="theme-card ${isSel}" id="t-card-${t.id}" onclick="window.ThemeEngine.selectTheme('${t.id}')">
                    <div class="theme-emoji-wrap">
                        <span class="theme-emoji">${t.emoji}</span>
                    </div>
                    <div class="theme-info">
                        <span class="theme-name">${t.name}</span>
                        <div class="theme-swatch-row">${swatchesHtml}</div>
                    </div>
                    ${t.id === curr ? '<div class="theme-sel-badge">✓</div>' : ''}
                </div>
            `;
        });

        html += `</div>`;
        panel.innerHTML = html;

        body.appendChild(overlay);
        body.appendChild(panel);
    },

    openPicker: function() {
        document.getElementById('s2p-theme-overlay')?.classList.add('show');
        document.getElementById('s2p-theme-panel')?.classList.add('show');
    },

    closePicker: function() {
        document.getElementById('s2p-theme-overlay')?.classList.remove('show');
        document.getElementById('s2p-theme-panel')?.classList.remove('show');
    },

    selectTheme: function(themeId) {
        this.apply(themeId, true);
        
        // Update picker UI if it exists
        document.querySelectorAll('.theme-card').forEach(c => {
            c.classList.remove('selected');
            const badge = c.querySelector('.theme-sel-badge');
            if (badge) badge.remove();
        });
        
        const selCard = document.getElementById(`t-card-${themeId}`);
        if(selCard) {
            selCard.classList.add('selected');
            selCard.insertAdjacentHTML('beforeend', '<div class="theme-sel-badge">✓</div>');
        }

        this.closePicker();
    },

    /* ==============================================
       CANVAS BACKGROUND SYSTEM
       ============================================== */
    canvasInitialized: false,
    animFrameId: null,

    initCanvasBackground: function() {
        if (!document.getElementById('s2p-theme-canvas')) {
            const canvas = document.createElement('canvas');
            canvas.id = 's2p-theme-canvas';
            canvas.style.cssText = 'position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:0; pointer-events:none;';
            document.body.prepend(canvas);
            
            window.addEventListener('resize', () => {
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
                // Force a re-render on resize to avoid stretching
                this.renderCanvasBackground(this.get());
            });
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            this.canvasInitialized = true;
        }
        this.renderCanvasBackground(this.get());
    },

    renderCanvasBackground: function(themeId) {
        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }
        
        const canvas = document.getElementById('s2p-theme-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        if (themeId === 'dark') this.drawDark(ctx, w, h);
        else if (themeId === 'love') this.drawLove(ctx, w, h);
        else if (themeId === 'galaxy') this.drawGalaxy(ctx, w, h);
        else if (themeId === 'panda') this.drawPanda(ctx, w, h);
        else if (themeId === 'penguin') this.drawPenguin(ctx, w, h);
        else if (themeId === 'sunset') this.drawSunset(ctx, w, h);
        else if (themeId === 'neon') this.drawNeon(ctx, w, h);
        // light has no canvas animation
    },

    drawDark: function(ctx, w, h) {
        const motes = Array.from({length:30},()=>({
            x: Math.random()*w, y: Math.random()*h,
            r: Math.random()*1.5+0.3, dx: (Math.random()-.5)*0.2, dy: (Math.random()-.5)*0.15, a: Math.random()
        }));
        const frame = () => {
            ctx.clearRect(0,0,w,h);
            motes.forEach(m=>{
                m.x+=m.dx; m.y+=m.dy; m.a+=0.005;
                if(m.x<0)m.x=w; if(m.x>w)m.x=0;
                if(m.y<0)m.y=h; if(m.y>h)m.y=0;
                ctx.beginPath();
                ctx.arc(m.x,m.y,m.r,0,Math.PI*2);
                ctx.fillStyle=`rgba(203,166,247,${0.2+0.15*Math.sin(m.a)})`;
                ctx.fill();
            });
            this.animFrameId = requestAnimationFrame(frame);
        };
        frame();
    },

    drawLove: function(ctx, w, h) {
        const hearts = Array.from({length:14},()=>({
            x: Math.random()*w, y: Math.random()*h+h, size: Math.random()*10+6,
            speed: Math.random()*0.5+0.3, drift: (Math.random()-.5)*0.5,
            opacity: Math.random()*0.4+0.1, rot: Math.random()*0.1-.05
        }));
        const drawHeart = (ctx,x,y,size,opacity) => {
            ctx.save(); ctx.globalAlpha=opacity; ctx.fillStyle='#FF4D8D'; ctx.beginPath();
            ctx.moveTo(x,y);
            ctx.bezierCurveTo(x,y-size*.35,x-size*.5,y-size*.65,x-size*.5,y-size*.35);
            ctx.bezierCurveTo(x-size*.5,y-size*.65,x,y-size*.85,x,y-size*.5);
            ctx.bezierCurveTo(x,y-size*.85,x+size*.5,y-size*.65,x+size*.5,y-size*.35);
            ctx.bezierCurveTo(x+size*.5,y-size*.65,x,y-size*.35,x,y);
            ctx.fill(); ctx.restore();
        };
        const frame = () => {
            ctx.clearRect(0,0,w,h);
            hearts.forEach(heart=>{
                heart.y -= heart.speed; heart.x += heart.drift;
                if(heart.y < -20){ heart.y=h+20; heart.x=Math.random()*w; }
                drawHeart(ctx, heart.x, heart.y, heart.size, heart.opacity);
            });
            this.animFrameId = requestAnimationFrame(frame);
        };
        frame();
    },

    drawGalaxy: function(ctx, w, h) {
        let t = 0;
        const starColors = [[255,255,255],[220,235,255],[200,220,255],[255,250,220],[255,240,180]];
        const layers = [
            Array.from({length:80},()=>({x:Math.random()*w, y:Math.random()*h, r:Math.random()*.5+.15, speed:.05, col:starColors[Math.floor(Math.random()*starColors.length)], twinkleOffset:Math.random()*Math.PI*2})),
            Array.from({length:35},()=>({x:Math.random()*w, y:Math.random()*h, r:Math.random()*.8+.35, speed:.14, col:starColors[Math.floor(Math.random()*starColors.length)], twinkleOffset:Math.random()*Math.PI*2})),
            Array.from({length:12},()=>({x:Math.random()*w, y:Math.random()*h, r:Math.random()*1.2+.6, speed:.28, col:starColors[Math.floor(Math.random()*starColors.length)], twinkleOffset:Math.random()*Math.PI*2}))
        ];
        let shoot={active:false,x:0,y:0,dx:0,dy:0,life:0,max:0,trail:[]};
        const launchShoot = () => {
            shoot.active=true; shoot.x=w*(.1+Math.random()*.6); shoot.y=Math.random()*(h*.4);
            const spd=5+Math.random()*3; shoot.dx=Math.cos(Math.PI*.15+Math.random()*.2)*spd; shoot.dy=Math.sin(Math.PI*.15+Math.random()*.2)*spd;
            shoot.max=25+Math.random()*15; shoot.life=shoot.max; shoot.trail=[];
        };
        const frame = () => {
            ctx.clearRect(0,0,w,h); t+=0.007;
            const mw = ctx.createLinearGradient(0, h*.1, w, h*.9);
            mw.addColorStop(0,'transparent'); mw.addColorStop(0.3,'rgba(60,90,180,0.07)'); mw.addColorStop(0.5,'rgba(80,120,220,0.12)'); mw.addColorStop(0.7,'rgba(60,90,180,0.07)'); mw.addColorStop(1,'transparent');
            ctx.fillStyle=mw; ctx.fillRect(0,0,w,h);
            const neb = ctx.createRadialGradient(w*.65+Math.sin(t*.4)*15,h*.25,0,w*.65,h*.25,w*.55);
            neb.addColorStop(0,'rgba(30,60,140,0.09)'); neb.addColorStop(0.6,'rgba(20,40,100,0.05)'); neb.addColorStop(1,'transparent');
            ctx.fillStyle=neb; ctx.fillRect(0,0,w,h);
            layers.forEach(layer=>{
                layer.forEach(s=>{
                    s.y+=s.speed; if(s.y>h){s.y=0;s.x=Math.random()*w;}
                    const tw = 0.55+0.45*Math.sin(t*2.5+s.twinkleOffset);
                    const [r,g,b]=s.col;
                    ctx.beginPath(); ctx.arc(s.x,s.y,s.r,0,Math.PI*2); ctx.fillStyle=`rgba(${r},${g},${b},${tw})`; ctx.fill();
                    if(s.r>0.9 && tw>0.85){
                        ctx.strokeStyle=`rgba(${r},${g},${b},${tw*.4})`; ctx.lineWidth=0.5;
                        ctx.beginPath(); ctx.moveTo(s.x-s.r*3,s.y); ctx.lineTo(s.x+s.r*3,s.y); ctx.moveTo(s.x,s.y-s.r*3); ctx.lineTo(s.x,s.y+s.r*3); ctx.stroke();
                    }
                });
            });
            if(!shoot.active && Math.random()<0.012) launchShoot();
            if(shoot.active){
                shoot.trail.push({x:shoot.x,y:shoot.y}); if(shoot.trail.length>18) shoot.trail.shift();
                for(let i=1;i<shoot.trail.length;i++){
                    const prog=i/shoot.trail.length; ctx.beginPath(); ctx.moveTo(shoot.trail[i-1].x,shoot.trail[i-1].y); ctx.lineTo(shoot.trail[i].x,shoot.trail[i].y);
                    ctx.strokeStyle=`rgba(200,225,255,${prog*0.85})`; ctx.lineWidth=prog*2.5; ctx.stroke();
                }
                const headGlow=ctx.createRadialGradient(shoot.x,shoot.y,0,shoot.x,shoot.y,6);
                headGlow.addColorStop(0,'rgba(255,255,255,0.9)'); headGlow.addColorStop(1,'transparent');
                ctx.fillStyle=headGlow; ctx.fillRect(shoot.x-6,shoot.y-6,12,12);
                shoot.x+=shoot.dx; shoot.y+=shoot.dy; shoot.life--;
                if(shoot.life<=0||shoot.x>w||shoot.y>h) shoot.active=false;
            }
            this.animFrameId = requestAnimationFrame(frame);
        };
        frame();
    },

    drawPanda: function(ctx, w, h) {
        const leaves = Array.from({length:10},()=>({
            x: Math.random()*w, y: Math.random()*h, size: Math.random()*14+8, speed: Math.random()*.3+.1,
            drift: (Math.random()-.5)*.3, rot: Math.random()*Math.PI*2, rotSpeed: (Math.random()-.5)*.02, opacity: Math.random()*0.2+0.06
        }));
        const drawLeaf = (ctx,x,y,size,rot,opacity) => {
            ctx.save(); ctx.translate(x,y); ctx.rotate(rot); ctx.globalAlpha=opacity; ctx.fillStyle='#2D9A5F';
            ctx.beginPath(); ctx.ellipse(0,0,size*.3,size,0,0,Math.PI*2); ctx.fill(); ctx.restore();
        };
        const frame = () => {
            ctx.clearRect(0,0,w,h);
            leaves.forEach(l=>{
                l.y+=l.speed; l.x+=l.drift; l.rot+=l.rotSpeed;
                if(l.y>h+20){l.y=-20;l.x=Math.random()*w;}
                drawLeaf(ctx,l.x,l.y,l.size,l.rot,l.opacity);
            });
            this.animFrameId = requestAnimationFrame(frame);
        };
        frame();
    },

    drawPenguin: function(ctx, w, h) {
        const flakes = Array.from({length:22},()=>({
            x:Math.random()*w, y:Math.random()*h, size:Math.random()*9+5, speed:Math.random()*.6+.3,
            drift:Math.random()*.4-.2, rot:Math.random()*Math.PI/3, rotSpeed:(Math.random()-.5)*.015, opacity:Math.random()*.55+.35
        }));
        const dots = Array.from({length:40},()=>({
            x:Math.random()*w, y:Math.random()*h, r:Math.random()*.8+.2, speed:Math.random()*.25+.08, drift:(Math.random()-.5)*.15, opacity:Math.random()*.3+.1
        }));
        let t=0;
        const drawCrystal = (x,y,size,rot,opacity) => {
            ctx.save(); ctx.translate(x,y); ctx.rotate(rot); ctx.globalAlpha=opacity; ctx.strokeStyle='#ffffff'; ctx.lineWidth=1.2;
            for(let i=0;i<6;i++){
                ctx.save(); ctx.rotate(i*Math.PI/3); ctx.beginPath(); ctx.moveTo(0,0); ctx.lineTo(0,-size); ctx.stroke();
                const b=size*.45; ctx.beginPath(); ctx.moveTo(0,-b*.7); ctx.lineTo(size*.28,-b*.7-size*.18); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(0,-b*.7); ctx.lineTo(-size*.28,-b*.7-size*.18); ctx.stroke(); ctx.restore();
            }
            ctx.beginPath(); ctx.arc(0,0,1.2,0,Math.PI*2); ctx.fillStyle='#fff'; ctx.fill(); ctx.restore();
        };
        const frame = () => {
            ctx.clearRect(0,0,w,h); t+=0.012;
            const g1=ctx.createRadialGradient(w*.15+Math.sin(t*.7)*25,h*.05,0,w*.15,h*.05,w*.6);
            g1.addColorStop(0,'rgba(93,173,226,0.1)'); g1.addColorStop(1,'transparent');
            ctx.fillStyle=g1; ctx.fillRect(0,0,w,h);
            const g2=ctx.createRadialGradient(w*.8+Math.cos(t*.5)*20,h*.9,0,w*.8,h*.9,w*.5);
            g2.addColorStop(0,'rgba(147,210,248,0.08)'); g2.addColorStop(1,'transparent');
            ctx.fillStyle=g2; ctx.fillRect(0,0,w,h);
            dots.forEach(d=>{
                d.y+=d.speed; d.x+=d.drift; if(d.y>h){d.y=0;d.x=Math.random()*w;}
                ctx.beginPath(); ctx.arc(d.x,d.y,d.r,0,Math.PI*2); ctx.fillStyle=`rgba(255,255,255,${d.opacity})`; ctx.fill();
            });
            flakes.forEach(f=>{
                f.y+=f.speed; f.x+=f.drift; f.rot+=f.rotSpeed; if(f.y>h+20){f.y=-20;f.x=Math.random()*w;}
                drawCrystal(f.x,f.y,f.size,f.rot,f.opacity);
            });
            this.animFrameId = requestAnimationFrame(frame);
        };
        frame();
    },

    drawSunset: function(ctx, w, h) {
        let t=0; const SX = w*.5, SY = -h*.05;
        const sparks = Array.from({length:35},()=>({
            x:Math.random()*w, y:Math.random()*h, r:Math.random()*2.5+0.8,
            speed:Math.random()*.35+.12, drift:(Math.random()-.5)*.35, opacity:Math.random()*.5+.15, phase:Math.random()*Math.PI*2
        }));
        const frame = () => {
            ctx.clearRect(0,0,w,h); t+=0.014;
            const vign=ctx.createRadialGradient(w*.5,0,0,w*.5,h*.3,w*.9);
            vign.addColorStop(0,'rgba(255,200,60,0.18)'); vign.addColorStop(0.5,'rgba(255,140,40,0.08)'); vign.addColorStop(1,'rgba(180,60,10,0.05)');
            ctx.fillStyle=vign; ctx.fillRect(0,0,w,h);
            const N=14;
            for(let i=0;i<N;i++){
                const base=(i/(N-1)-0.5)*Math.PI*.9; const angle=base+Math.sin(t*.6+i*.7)*.02; const len=h*1.45;
                ctx.save(); ctx.translate(SX,SY); ctx.rotate(angle);
                const roll=1-Math.abs((i/(N-1))-.5)*1.7; const inten=(0.05+0.022*Math.sin(t*.8+i*.5))*Math.max(0,roll);
                const ray=ctx.createLinearGradient(0,0,0,len);
                ray.addColorStop(0,`rgba(255,210,90,${Math.min(0.45,inten*3)})`); ray.addColorStop(0.18,`rgba(255,165,55,${Math.min(0.25,inten*2)})`);
                ray.addColorStop(0.55,`rgba(255,110,30,${Math.min(0.12,inten)})`); ray.addColorStop(1,'transparent');
                ctx.fillStyle=ray; const sp=5+Math.abs(Math.sin(angle))*9; ctx.fillRect(-sp,0,sp*2,len); ctx.restore();
            }
            const corona=ctx.createRadialGradient(SX,SY,0,SX,SY,w*.5);
            corona.addColorStop(0,`rgba(255,235,130,${0.24+0.06*Math.sin(t)})`); corona.addColorStop(0.3,`rgba(255,185,65,${0.10+0.03*Math.sin(t+1)})`);
            corona.addColorStop(0.7,'rgba(255,120,30,0.04)'); corona.addColorStop(1,'transparent');
            ctx.fillStyle=corona; ctx.fillRect(0,0,w,h);
            sparks.forEach(s=>{
                s.y-=s.speed; s.x+=s.drift; s.phase+=0.04; if(s.y<-10){s.y=h+10;s.x=Math.random()*w;} if(s.x<0)s.x=w; if(s.x>w)s.x=0;
                const glow=s.opacity*(0.55+0.45*Math.sin(s.phase)); const sg=ctx.createRadialGradient(s.x,s.y,0,s.x,s.y,s.r*3.5);
                sg.addColorStop(0,`rgba(255,225,80,${glow})`); sg.addColorStop(1,'transparent');
                ctx.fillStyle=sg; ctx.fillRect(s.x-s.r*3.5,s.y-s.r*3.5,s.r*7,s.r*7);
                ctx.beginPath(); ctx.arc(s.x,s.y,s.r*.55,0,Math.PI*2); ctx.fillStyle=`rgba(255,248,170,${Math.min(1,glow*1.3)})`; ctx.fill();
            });
            const horiz=ctx.createLinearGradient(0,h*.7,0,h); horiz.addColorStop(0,'rgba(255,130,30,0.10)'); horiz.addColorStop(1,'rgba(200,70,10,0.04)');
            ctx.fillStyle=horiz; ctx.fillRect(0,h*.7,w,h*.3);
            this.animFrameId = requestAnimationFrame(frame);
        };
        frame();
    },

    drawNeon: function(ctx, w, h) {
        let t=0; const orbs=[{x:w*.3,y:h*.4,r:100,c:'0,229,255'},{x:w*.7,y:h*.6,r:80,c:'213,0,249'}];
        const frame = () => {
            ctx.clearRect(0,0,w,h); t+=0.02;
            ctx.strokeStyle='rgba(0,229,255,0.04)'; ctx.lineWidth=0.5; const gs=36;
            for(let x=0;x<w;x+=gs){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}
            for(let y=0;y<h;y+=gs){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
            orbs.forEach((o,i)=>{
                const pulse = 0.04+0.03*Math.sin(t*1.5+i*Math.PI);
                const grd = ctx.createRadialGradient(o.x,o.y,0,o.x,o.y,o.r);
                grd.addColorStop(0,`rgba(${o.c},${pulse*2})`); grd.addColorStop(0.5,`rgba(${o.c},${pulse})`); grd.addColorStop(1,'transparent');
                ctx.fillStyle=grd; ctx.fillRect(0,0,w,h);
            });
            const lineY = ((t*30)%h); const lineGrd = ctx.createLinearGradient(0,lineY-2,0,lineY+2);
            lineGrd.addColorStop(0,'transparent'); lineGrd.addColorStop(0.5,'rgba(0,229,255,0.15)'); lineGrd.addColorStop(1,'transparent');
            ctx.fillStyle=lineGrd; ctx.fillRect(0,lineY-2,w,4);
            this.animFrameId = requestAnimationFrame(frame);
        };
        frame();
    }
};

// Auto-init immediately when script runs in <head>
window.ThemeEngine.init();
