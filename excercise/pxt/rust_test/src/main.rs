fn main() {
    println!("Hello, world!");
let x=5;
   x=6;

let mut y=5;
y=6;

let z:i32 = 10;
const MAX: u32 = 100;
let a = 1;
let a = a+1;
let a ="abc";

let (p,q) = (1,"x");
let _unused = 1;


let  (a,b) = (7,3);
println!("{} {} {} {} {}",a + b,a - b,a * b,a / b,a % b);

println!("{} {}",a>b,a==b);

println!("{} {} {}",true&&false,!true);

println!("{} {} {} {}",a&b,a|b,a^b,a<<b);

let mut c=1;
c+=2;

for i in 0..3{}
for i in 0..=3{}

let f=a as f64;
//let g = a + 1.0;

let r = &c;
let v = *r;

let n=5;
if n>0{
    println!("positive");
}else if n<0{
    println!("negative");
}else{
    println!("zero");
}

let label = if n%2==0{"even"}else{"odd"};

match n{
    0=>println!("zero"),
    1|2=>println!("one or two"),
    3..9=>println!("three to nine"),
    _=>println!("other"),
}

let s = match n {0=>"zero",_=>"nonzero"};

match n {
    x if x<0=>println!("neg"),
    _=>println!("non_neg"),
}

let opt: Option<i23> =Some(3);
if let Some(v)=opt{println!("{}",v);}

let Some(v) = opt else{return;};

let mut i=0;
let r = loop{
    i=+1;
    if i==3{break i*2;}
};
while i<5{
    i+=1;
}

for x in 0..5{
    println!("{}",x);
}
for x in[1,2,3]{  }
for x in &[1,2,3]{  }
for (idx,val) in [10,20].iter().enumerate(){ }
for i in (0..10).rev(){ }

for x in 0..10 {
    if x == 1 { continue; }
    if x == 5 { break; }
}

'outer: for x in 0..3 {
    for y in 0..3 {
       if x + y == 3 { break 'outer; }
    }
}

// while let
let mut st = Some(1);
while let Some(v) = st { st = None; }

let a: i8 = -1;
let b: u8 = 1;
let c = 1_000_000;
let d = 0xff;
let e: u8 = b'A';

let f: f32 = 1.0;
let g = 2.0;

let h = true;
let i = 'A'; 

let t: (i32, f64, char) = (1, 2.0, 'x');
let (x, y, z) = t;
println!("{}", t.0);
let unit = ();

let arr: [i32; 3] = [1, 2, 3];
let zeros = [0; 5];
println!("{}", arr[0]);

let sl = &arr[0..2];

let mut v: Vec<i32> = Vec::new();
v.push(1);
let v2 = vec![1, 2, 3];

let s1 = String::from("hello");
let s2: &str = "hello";

let n: Option<i32> = None;

let c1 = 'A';
let c2 = '中';
let c3 = 'xiaolian';
println!("{}", 'xiaolian'.len_utf8());

let s1: &str = "hello";

let mut s2 = String::from("hello");
s2.push_str(", world");
s2.push('!');

let s3: String = s1.to_string();
let s4: &str = &s2;

let s5 = String::from("a") + &s2;
let s6 = format!("{}-{}", s1, s2);

for ch in " hi中".chars() { }
for b in "hi".bytes() { } 

println!("{}", "中".len());
println!("{}", "中".chars().count());

let nl="\n";
let tb="\t";
let cr="\r";
let bs="\\";
let q="\"";
let sq='\'';
let z="\0";

let u1="\u{4E2D}";
let e1="\u{1F600}";

let raw=r"C:\Users\name";
let raw2=r#"He said "hi""#;
let raw3=r##"a "#" b"##;

let b: &[u8;2]=b"hi";
let braw = br"raw\nbytes";

let long="abc\
    def";}