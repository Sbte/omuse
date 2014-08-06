module qgmodel

  implicit none
  integer    :: i,counter,savecounter,save_num,max_it,free_slip, &
              & Nx,Ny,Nt,Nm !,restart,restart_num
  real(8)    :: tau,A_H,R_H,H,rho,beta0,Lx,Ly,lambda0,lambda1,e111,phi1z0, &
              & dx,dy,dt,T,t_curr,err_tol,relax_coef
  real(8)    :: begin_time, wind_sigma
  real(8), allocatable,dimension (:,:)   :: max_psi
  real(8), allocatable,dimension (:,:,:) :: psi_1,psi_2,inter,chii,chi_prev, &
                                          & vis_bot_prev,vis_bot_curr, &
                                          & vis_lat_prev,vis_lat_curr
  character(len=25) :: filename

contains

function initialize_code() result(ret)
  integer :: ret
  ret=0

  call mkl_set_dynamic(0)
  call mkl_set_num_threads( 4 )

  call default_numerical_parameters()
  call default_physical_parameters()
    
end function

subroutine default_numerical_parameters()
  Lx             = 4000000.d0
  Ly             = 4000000.d0
  dx             = 10000.d0
  dy             = 10000.d0
  dt             = 1800.d0
  T              = 86400.d0
  savecounter    = 48
  err_tol        = 1.0d-6
  max_it         = 20000
  relax_coef     = 1.7d0
  free_slip      = 1
!  restart        = 0  ! not used for amuse
!  restart_num    = 360 ! not used                
end subroutine  

subroutine default_physical_parameters()
  begin_time = 0.0
  wind_sigma = 1.0
  
  tau        = 0.05d0
  A_H        = 100.d0
  R_H        = 0.d0
  lambda0    = 0.d0
  lambda1    = 2.0000d-05
  e111       = 0.d0
  phi1z0     = 1.4142135623731d0
  H          = 4000.d0
  rho        = 1000.d0
  beta0      = 1.8616d-11
  Nm         = 1
end subroutine

subroutine initialize_arrays() 
! properly should have some check whether allocations succeeded and return 
! the non-zero ret value

  allocate (psi_1(Nm,Nx,Ny))
  psi_1(:,:,:)        = 0.d0
  allocate (psi_2(Nm,Nx,Ny))
  psi_2(:,:,:)        = 0.d0
  allocate (inter(Nm,Nx,Ny))
  inter(:,:,:)        = 0.d0
  allocate (chii(Nm,Nx,Ny))
  chii(:,:,:)         = 0.d0
  allocate (chi_prev(Nm,Nx,Ny))
  chi_prev(:,:,:)     = 0.d0
  allocate (vis_bot_prev(Nm,Nx,Ny))
  vis_bot_prev(:,:,:) = 0.d0
  allocate (vis_bot_curr(Nm,Nx,Ny))
  vis_bot_curr(:,:,:) = 0.d0
  allocate (vis_lat_prev(Nm,Nx,Ny))
  vis_lat_prev(:,:,:) = 0.d0
  allocate (vis_lat_curr(Nm,Nx,Ny))
  vis_lat_curr(:,:,:) = 0.d0
  allocate (max_psi(Nm,Nt))
  max_psi(:,:) = 0.d0

end subroutine

function commit_parameters() result(ret)
  integer :: ret

  Nx = Lx/dx + 1
  Ny = Ly/dy + 1
  !Nt = T/dt + 1
  Nt = INT(T/dt)/savecounter + 1

  call initialize_arrays()

  t_curr   = begin_time

  ret=0
end function

function initialize_grid() result(ret)
  integer :: ret

! naive initialization of psi_2
  psi_2=psi_1
  chi_prev=0.
! note in principle the only way to restart consistently is by writing and
! reading psi_2 and chi_prev! 
! note chi_prev does not actually do anything atm
! psi_2 may be initialized by a warm up step...

! initialize vis_*_prev from pis_2
  call vis_bot(Nm,Nx,Ny,free_slip,psi_2,vis_bot_prev)
  call vis_lat(Nm,Nx,Ny,free_slip,psi_2,vis_lat_prev)

! initialize vis_*_curr from pis_1
  call vis_bot(Nm,Nx,Ny,free_slip,psi_1,vis_bot_curr)
  call vis_lat(Nm,Nx,Ny,free_slip,psi_1,vis_lat_curr)

! chi is already calculated here so it becomes available for other codes
  call chi(tau,A_H,R_H,Lx,Ly,lambda0,lambda1,e111,phi1z0, &
       &    Nm,Nx,Ny,dx,H,rho,beta0,err_tol,max_it,relax_coef, &
       &    psi_1,free_slip,vis_bot_curr,vis_bot_prev,vis_lat_prev,chi_prev, &
       &    chii)
  counter=counter+1
  ret=0
end function

function evolve_model(tend) result(ret)
  integer :: ret
  integer :: save_num
  real(8) :: tend
  
  do while ( t_curr < tend)
      
   t_curr = t_curr + dt
       
  !Robert-Asselin filter
   inter = psi_2 + 2.d0*dt*chii
   psi_1 = psi_1 + 0.1d0*(inter-2.d0*psi_1+psi_2)
   psi_2 = inter
  !!!
  ! do exactly the same thing again with opposite psi arrays
  ! (specials: leap-frog time stepping, and using previous viscosity)
   t_curr = t_curr + dt
   
   chi_prev = chii
   vis_bot_prev  = vis_bot_curr
   call vis_bot(Nm,Nx,Ny,free_slip,psi_2,vis_bot_curr)
   vis_lat_prev  = vis_lat_curr
   call vis_lat(Nm,Nx,Ny,free_slip,psi_2,vis_lat_curr)
   call chi(tau,A_H,R_H,Lx,Ly,lambda0,lambda1,e111,phi1z0, &
       &    Nm,Nx,Ny,dx,H,rho,beta0,err_tol,max_it,relax_coef, &
       &    psi_2,free_slip,vis_bot_curr,vis_bot_prev,vis_lat_prev,chi_prev, &
       &    chii)
   counter = counter + 1

  !Robert-Asselin filter
   inter = psi_1 + 2.d0*dt*chii
   psi_2 = psi_2 + 0.1d0*(inter-2.d0*psi_2+psi_1)
   psi_1 = inter
  !!!

   chi_prev = chii
  ! update viscosity
   vis_bot_prev  = vis_bot_curr
   call vis_bot(Nm,Nx,Ny,free_slip,psi_1,vis_bot_curr)
   vis_lat_prev  = vis_lat_curr
   call vis_lat(Nm,Nx,Ny,free_slip,psi_1,vis_lat_curr)
  !find chi, and take a step
   call chi(tau,A_H,R_H,Lx,Ly,lambda0,lambda1,e111,phi1z0, &
       &    Nm,Nx,Ny,dx,H,rho,beta0,err_tol,max_it,relax_coef, &
       &    psi_1,free_slip,vis_bot_curr,vis_bot_prev,vis_lat_prev,chi_prev, &
       &    chii)
   counter = counter + 1
 
  enddo
  ret=0
end function

function get_counter(c) result (ret)
  integer :: ret,c
  c=counter
  ret=0
end function

function get_time(tnow) result (ret)
  integer :: ret
  real(8) :: tnow
  tnow=t_curr
  ret=0
end function

function set_time(tnow) result (ret)
  integer :: ret
  real(8) :: tnow
  t_curr=tnow
  ret=0
end function

function get_begin_time(t) result (ret)
  integer :: ret
  real(8) :: t
  t=begin_time
  ret=0
end function

function set_begin_time(t) result (ret)
  integer :: ret
  real(8) :: t
  begin_time=t
  ret=0
end function

function get_wind_sigma(t) result (ret)
  integer :: ret
  real(8) :: t
  t=wind_sigma
  ret=0
end function

function set_wind_sigma(t) result (ret)
  integer :: ret
  real(8) :: t
  wind_sigma=t
  ret=0
end function

function cleanup_code() result(ret)
  integer :: ret
  ret=0
end function

function get_dpsi_dt(i,j,k,dpsi,n) result(ret)
  integer :: ret,n
  integer :: ii,i(n),j(n),k(n)
  real(8) :: dpsi(n)
  
  do ii=1,n
    dpsi(ii)=chii(k(ii),i(ii),j(ii))
  enddo
  ret=0
end function

function get_psi1_state(i,j,k,psi1,n) result(ret)
  integer :: ret,n
  integer :: ii,i(n),j(n),k(n)
  real(8) :: psi1(n)
  
  do ii=1,n
    psi1(ii)=psi_1(k(ii),i(ii),j(ii))
  enddo
  ret=0
end function

function get_psi2_state(i,j,k,psi2,n) result(ret)
  integer :: ret,n
  integer :: ii,i(n),j(n),k(n)
  real(8) :: psi2(n)
  
 do ii=1,n
    psi2(ii)=psi_2(k(ii),i(ii),j(ii))
  enddo
  ret=0
end function

function set_psi1_state(i,j,k,psi1,n) result(ret)
  integer :: ret,n
  integer :: ii,i(n),j(n),k(n)
  real(8) :: psi1(n)
  
 do ii=1,n
   psi_1(k(ii),i(ii),j(ii))= psi1(ii)
  enddo
  ret=0
  ret=0
end function

function set_psi2_state(i,j,k,psi2,n) result(ret)
   integer :: ret,n
  integer :: ii,i(n),j(n),k(n)
  real(8) :: psi2(n)

  do ii=1,n
    psi_2(k(ii),i(ii),j(ii))=psi2(ii)
  enddo
  ret=0
end function

function get_position_of_index(i,j,k,x,y,n) result(ret)
  integer :: ret,n
  integer :: ii,i(n),j(n),k(n)
  real(8) :: x(n),y(n)
  
  do ii=1,n
    x(ii)=(i(ii)-1)*dx
    y(ii)=(j(ii)-1)*dy
  enddo
  ret=0
end function



function recommit_parameters() result(ret)
  integer :: ret
  ret=0
end function

! here come the parameter getters and setters

function get_Lx(x) result (ret)
  integer :: ret
  real(8) :: x
  x=Lx
  ret=0
end function

function set_Lx(x) result (ret)
  integer :: ret
  real(8) :: x
  Lx=x
  ret=0
end function

function get_Ly(x) result (ret)
  integer :: ret
  real(8) :: x
  x=Ly
  ret=0
end function

function set_Ly(x) result (ret)
  integer :: ret
  real(8) :: x
  Ly=x
  ret=0
end function

function get_dy(x) result (ret)
  integer :: ret
  real(8) :: x
  x=dy
  ret=0
end function

function set_dy(x) result (ret)
  integer :: ret
  real(8) :: x
  dy=x
  ret=0
end function

function get_dx(x) result (ret)
  integer :: ret
  real(8) :: x
  x=dx
  ret=0
end function

function set_dx(x) result (ret)
  integer :: ret
  real(8) :: x
  dx=x
  ret=0
end function

function get_dt(x) result (ret)
  integer :: ret
  real(8) :: x
  x=2*dt
  ret=0
end function

function set_dt(x) result (ret)
  integer :: ret
  real(8) :: x
  dt=x/2
  ret=0
end function

function get_T(x) result (ret)
  integer :: ret
  real(8) :: x
  x=T
  ret=0
end function

function set_T(x) result (ret)
  integer :: ret
  real(8) :: x
  T=x
  ret=0
end function

function get_A_H(x) result (ret)
  integer :: ret
  real(8) :: x
  x=A_H
  ret=0
end function

function set_A_H(x) result (ret)
  integer :: ret
  real(8) :: x
  A_H=x
  ret=0
end function

function get_R_H(x) result (ret)
  integer :: ret
  real(8) :: x
  x=R_H
  ret=0
end function

function set_R_H(x) result (ret)
  integer :: ret
  real(8) :: x
  R_H=x
  ret=0
end function

function get_lambda0(x) result (ret)
  integer :: ret
  real(8) :: x
  x=lambda0
  ret=0
end function

function set_lambda0(x) result (ret)
  integer :: ret
  real(8) :: x
  lambda0=x
  ret=0
end function

function get_lambda1(x) result (ret)
  integer :: ret
  real(8) :: x
  x=lambda1
  ret=0
end function

function set_lambda1(x) result (ret)
  integer :: ret
  real(8) :: x
  lambda1=x
  ret=0
end function

function get_e111(x) result (ret)
  integer :: ret
  real(8) :: x
  x=e111
  ret=0
end function

function set_e111(x) result (ret)
  integer :: ret
  real(8) :: x
  e111=x
  ret=0
end function

function get_phi1z0(x) result (ret)
  integer :: ret
  real(8) :: x
  x=phi1z0
  ret=0
end function

function set_phi1z0(x) result (ret)
  integer :: ret
  real(8) :: x
  phi1z0=x
  ret=0
end function

function get_H(x) result (ret)
  integer :: ret
  real(8) :: x
  x=H
  ret=0
end function

function set_H(x) result (ret)
  integer :: ret
  real(8) :: x
  H=x
  ret=0
end function

function get_rho(x) result (ret)
  integer :: ret
  real(8) :: x
  x=rho
  ret=0
end function

function set_rho(x) result (ret)
  integer :: ret
  real(8) :: x
  rho=x
  ret=0
end function

function get_beta0(x) result (ret)
  integer :: ret
  real(8) :: x
  x=beta0
  ret=0
end function

function set_beta0(x) result (ret)
  integer :: ret
  real(8) :: x
  beta0=x
  ret=0
end function

function get_savecounter(x) result (ret)
  integer :: ret,x
  x=savecounter
  ret=0
end function

function set_savecounter(x) result (ret)
  integer :: ret,x
  savecounter=x
  ret=0
end function

function get_tau(x) result (ret)
  integer :: ret
  real(8) :: x
  x=tau
  ret=0
end function

function set_tau(x) result (ret)
  integer :: ret
  real(8) :: x
  tau=x
  ret=0
end function

function get_err_tol(x) result (ret)
  integer :: ret
  real(8) :: x
  x=err_tol
  ret=0
end function

function set_err_tol(x) result (ret)
  integer :: ret
  real(8) :: x
  err_tol=x
  ret=0
end function

function get_max_it(x) result (ret)
  integer :: ret,x
  x=max_it
  ret=0
end function

function set_max_it(x) result (ret)
  integer :: ret,x
  max_it=x
  ret=0
end function

function get_relax_coef(x) result (ret)
  integer :: ret
  real(8) :: x
  x=relax_coef
  ret=0
end function

function set_relax_coef(x) result (ret)
  integer :: ret
  real(8) :: x
  relax_coef=x
  ret=0
end function

function get_free_slip(x) result (ret)
  integer :: ret,x
  x=free_slip
  ret=0
end function

function set_free_slip(x) result (ret)
  integer :: ret,x
  free_slip=x
  ret=0
end function

function get_Nx(x) result (ret)
  integer :: ret
  integer :: x
  x=Nx
  ret=0
end function
function get_Ny(x) result (ret)
  integer :: ret
  integer :: x
  x=Ny
  ret=0
end function
function get_Nm(x) result (ret)
  integer :: ret
  integer :: x
  x=Nm
  ret=0
end function
function set_Nm(x) result (ret)
  integer :: ret,x
  Nm=x
  ret=0
end function
function get_Nt(x) result (ret)
  integer :: ret
  integer :: x
  x=Nt
  ret=0
end function
end module

! move wind to here in order to...
subroutine wind(Nm,Nx,Ny,windy)
 use qgmodel, only: wind_sigma
implicit none
integer, intent(in) :: Nx,Ny,Nm
real(8), dimension(Nm,Nx,Ny), intent(out) :: windy

integer :: i,j,m
real(8) :: pi = 3.14159265358979d0
real(8), dimension(Nx,Ny) :: tau

tau(:,:)     = 0.d0
windy(:,:,:) = 0.d0

do i=1,Nx
 do j=1,Ny


! jan's:
  tau(i,j) = cos(2.*pi*((j-1.)/(Ny-1.)-0.5))+2.*sin(pi*((j-1.)/(Ny-1.)-0.5))
! dijkstra:
!   tau(i,j)= - ( wind_sigma*cos(pi*(j-1.)/(Ny-1.))+(1-wind_sigma)*cos(2.*pi*((j-1.)/(Ny-1.))) )

!  tau(i,j) = -1./(2.*pi)*cos(2.*pi*(j-1.)/(Ny-1.))
!  tau(i,j) = -cos(pi*(j-1.)/(Ny-1.))
!  tau(i,j) = -cos(pi*(j-1.5)/(ny-2.))                                             ! what they had in the code
!  tau(i,j) = -1./pi*cos(pi*(j-1.)/(Ny-1.))                                         ! what I used
!  tau(i,j) = -1./pi*cos(pi*(j-1.)/(ny-1.))*sin(pi*(i-1.)/(ny-1.))                 ! Veronis (1966) ????

 end do
end do

do m=1,Nm
 do i=2,Nx-1
  do j=2,Ny-1

  windy(m,i,j) = -tau(i,j+1)+tau(i,j-1)                                            ! include the whole curl, i.e., also x-derivative for generality ?????

  end do
 end do
end do

!      write(*,*) tau
!      write(*,*) windy

end


!      real(8), allocatable, dimension (:,:) :: wind_term
!      allocate (wind_term(Nx,Ny))
!      call wind(Nx,Ny,wind_term)



