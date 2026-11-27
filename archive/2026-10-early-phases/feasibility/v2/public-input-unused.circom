pragma circom 2.2.3;
template UnusedPublic() { signal input bound; signal input unused; bound === 1; }
component main { public [bound, unused] } = UnusedPublic();
