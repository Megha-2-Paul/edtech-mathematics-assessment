/* Shared mathematics rendering helpers for teacher and student interfaces. */
(function () {
  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>\"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', "'": '&#039;'
    }[c]));
  }

  function latexSafe(value) {
    return String(value)
      .replace(/\\/g, '\\backslash ')
      .replace(/[{}]/g, m => '\\' + m);
  }

  function autoMath(text) {
    let out = escapeHtml(text);

    // Existing explicit MathJax delimiters are protected by temporarily replacing them.
    const protectedMath = [];
    out = out.replace(/\\\((.*?)\\\)/gs, (_, expr) => {
      const token = `@@MATH${protectedMath.length}@@`;
      protectedMath.push(`\\(${expr}\\)`);
      return token;
    });

    // Common assessment notation entered naturally by teachers:
    // tan 45° / (1 + tan^2 45°) -> a properly rendered fraction.
    // Also supports simple numeric/algebraic fractions such as 3 / 4.
    const fractionPattern = /((?:[A-Za-z]+(?:\s*\^\s*\d+)?(?:\s+\d+(?:\.\d+)?°?)?|\d+(?:\.\d+)?|\([^()]+\)))\s*\/\s*\(([^()]+)\)/g;
    out = out.replace(fractionPattern, (_, numerator, denominator) => {
      const n = latexSafe(numerator.trim());
      const d = latexSafe(denominator.trim()).replace(/\^\s*(\d+)/g, '^{$1}');
      return `\\(\\frac{${n}}{${d}}\\)`;
    });

    // Simple a / b fractions when both sides are compact math tokens.
    out = out.replace(/(?<![\w])([A-Za-zα-ωΑ-Ω]+|\d+(?:\.\d+)?)\s*\/\s*([A-Za-zα-ωΑ-Ω]+|\d+(?:\.\d+)?)(?![\w])/g,
      (_, numerator, denominator) => `\\(\\frac{${latexSafe(numerator)}}{${latexSafe(denominator)}}\\)`);

    // Natural superscripts: tan^2, x^2, x^10 -> x^{2}, x^{10}.
    out = out.replace(/([A-Za-zα-ωΑ-Ω)])\s*\^\s*(\d+)/g, '$1^{\$2}');

    protectedMath.forEach((math, i) => {
      out = out.replace(`@@MATH${i}@@`, math);
    });
    return out;
  }

  window.AssessmentMath = {
    escapeHtml,
    renderText(text) {
      return autoMath(text).replace(/\n/g, '<br>');
    },
    typeset(container) {
      if (window.MathJax?.typesetPromise) {
        window.MathJax.typesetClear?.([container]);
        window.MathJax.typesetPromise([container]).catch(() => {});
      }
    }
  };
})();
