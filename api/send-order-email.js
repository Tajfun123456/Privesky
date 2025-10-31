// api/send-order-email.js
import { Resend } from 'resend';

// Inicializace Resend klienta s API klíčem z Environment Variables
const resend = new Resend(process.env.RESEND_API_KEY);

// Adresa, kam se budou posílat notifikace o nových objednávkách
const ADMIN_EMAIL = 'sf.simonflorian@gmail.com'; // Vaše e-mailová adresa

export default async function handler(req, res) {
  // Povolíme pouze POST metodu
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  try {
    // Získáme data o objednávce z těla požadavku
    const { contact, order, shippingOption, pickupPoint } = req.body;

    if (!contact || !order) {
        return res.status(400).json({ error: 'Missing order data' });
    }

    // --- 1. Sestavení e-mailu pro VÁS (admina) ---
    const adminEmailHtml = `
        <h1>Nová objednávka! 🚀</h1>
        <p><strong>Číslo objednávky:</strong> ${order.orderId}</p>
        <hr>
        <h2>Kontaktní údaje</h2>
        <p><strong>E-mail:</strong> ${contact.email}</p>
        <p><strong>Telefon:</strong> ${contact.phone}</p>
        <hr>
        <h2>Doručení</h2>
        <p><strong>Způsob:</strong> ${shippingOption.name}</p>
        ${pickupPoint ? `
            <h3>Výdejní místo:</h3>
            <p>
                <strong>${pickupPoint.name}</strong><br>
                ${pickupPoint.street || ''}<br>
                ${pickupPoint.zip || ''} ${pickupPoint.city || ''}
            </p>
        ` : `
            <h3>Adresa:</h3>
            <p>
                ${contact.address.street} ${contact.address.number}<br>
                ${contact.address.zip} ${contact.address.city}
            </p>
        `}
        <hr>
        <h2>Položky</h2>
        <ul>
            ${order.items.map(item => `<li>${item.productName} (x${item.quantity}) - ${item.price} Kč</li>`).join('')}
        </ul>
        <hr>
        <h3>Mezisoučet: ${order.subtotal} Kč</h3>
        <h3>Doprava: ${order.shippingCost} Kč</h3>
        <h2>Celkem: ${order.total} Kč</h2>
    `;

    // --- 2. Sestavení e-mailu pro ZÁKAZNÍKA ---
    const customerEmailHtml = `
        <h1>Děkujeme za vaši objednávku! 🦊</h1>
        <p>Dobrý den, vaše objednávka č. <strong>${order.orderId}</strong> byla úspěšně přijata a brzy ji začneme zpracovávat.</p>
        <hr>
        <h2>Souhrn objednávky</h2>
        <p><strong>Způsob dopravy:</strong> ${shippingOption.name}</p>
        ${pickupPoint ? `
            <p><strong>Výdejní místo:</strong> ${pickupPoint.name}, ${pickupPoint.street || ''}, ${pickupPoint.zip || ''} ${pickupPoint.city || ''}</p>
        ` : `
            <p><strong>Doručovací adresa:</strong> ${contact.address.street} ${contact.address.number}, ${contact.address.zip} ${contact.address.city}</p>
        `}
        <hr>
        <ul>
            ${order.items.map(item => `<li>${item.productName} (x${item.quantity}) - ${item.price} Kč</li>`).join('')}
        </ul>
        <hr>
        <p><strong>Mezisoučet:</strong> ${order.subtotal} Kč</p>
        <p><strong>Doprava:</strong> ${order.shippingCost} Kč</p>
        <p><strong>Celkem k úhradě:</strong> ${order.total} Kč</p>
        <hr>
        <p>S pozdravem,<br>Tým 3D Přívěsky</p>
    `;

    // --- 3. Odeslání obou e-mailů ---
    await Promise.all([
      // E-mail pro admina
      resend.emails.send({
        from: 'Nová objednávka <onboarding@resend.dev>',
        to: ADMIN_EMAIL,
        subject: `Nová objednávka: ${order.orderId}`,
        html: adminEmailHtml,
      }),
      // E-mail pro zákazníka
      resend.emails.send({
        from: '3D Přívěsky <onboarding@resend.dev>',
        to: contact.email,
        subject: `Potvrzení objednávky č. ${order.orderId}`,
        html: customerEmailHtml,
      }),
    ]);

    // Pokud vše proběhlo, vrátíme úspěšnou odpověď
    res.status(200).json({ message: 'Emails sent successfully!' });

  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Failed to send emails.' });
  }
}